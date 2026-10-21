"""Worker process: `python -m app.workers.main [--once] [--kinds crawl,build,export]`.

Polls the durable job table, runs up to WORKER_CONCURRENCY jobs in threads, persists progress, events and
results, honours cancellation, and recovers jobs whose worker died (heartbeat expiry)."""
from __future__ import annotations

import argparse
import logging
import os
import socket
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select

from ..core.config import get_settings
from ..core.logging import configure_logging
from ..database.session import SessionLocal, session_scope
from ..models import Job, Source, StorybookStory
from ..services import jobs as jobsvc
from ..services import settings_service
from .crawl import run_crawl

log = logging.getLogger("app.worker")


def run_build_job(job: Job) -> None:
    from ..services.build import run_build
    deps = (job.params or {}).get("after") or []
    with SessionLocal() as db:
        if deps:
            pending = db.scalar(select(Job.id).where(Job.id.in_(deps), Job.status.in_(jobsvc.ACTIVE)).limit(1))
            if pending:  # wait for upstream crawls without consuming an attempt
                j = db.get(Job, job.id)
                j.status, j.locked_by, j.phase, j.attempts = "queued", None, "waiting_for_crawls", max(0, j.attempts - 1)
                j.run_after = datetime.now(timezone.utc) + timedelta(seconds=10)
                db.commit()
                return
    with SessionLocal() as db:
        def progress(phase: str, n: int) -> None:
            with SessionLocal() as pdb:
                jobsvc.add_event(pdb, job.id, f"Build phase: {phase} ({n})", phase=phase)
                jobsvc.heartbeat(pdb, job.id, phase=phase)
        try:
            jobsvc.add_event(db, job.id, "Knowledge-base build started", phase="build")
            db.commit()
            summary = run_build(db, job.id, progress)
            db.commit()
        except Exception as e:
            db.rollback()
            raise e
    with SessionLocal() as db:
        jobsvc.finish(db, job.id, "succeeded", result=summary, records_extracted=summary["records"])


def run_export_job(job: Job) -> None:
    from ..services.exports import generate
    with SessionLocal() as db:
        jobsvc.heartbeat(db, job.id, phase="generating")
        cfg = settings_service.get_config(db)
        res = generate(db, job.id, job.params["format"], job.params.get("resource", "all"), cfg["export_policy"].get("max_rows", 250000))
        jobsvc.finish(db, job.id, "succeeded", result=res, records_extracted=res["row_count"])


def _persist_hosts(db, job_id, reason: str) -> list[str]:
    """Persist hosts approved during verification into the audited approved-domain list."""
    from ..scrapers.dskb import core as engine
    from ..services.audit import audit
    cfg = settings_service.get_config(db)
    known = set(cfg["approved_domains"])
    new = sorted(h for h in engine.FETCHER.extra_allow if h and h not in known and "." in h and not any(h == d or h.endswith("." + d) for d in known))
    if new:
        settings_service.update_config(db, {"approved_domains": sorted(known | set(new))})
        audit(db, None, "config.approve_domains", "config", None, job_id=str(job_id), reason=reason, domains=new)
    return new


def run_review_job(job: Job) -> None:
    from ..services.review_resolver import process_queue
    with SessionLocal() as db:
        def progress(n: int, total: int, msg: str) -> None:
            with SessionLocal() as pdb:
                if n % 5 == 0 or n == total:
                    jobsvc.add_event(pdb, job.id, f"[{n}/{total}] {msg}", phase="resolving")
                jobsvc.heartbeat(pdb, job.id, phase="resolving", urls_processed=n, urls_discovered=total)
        summary = process_queue(db, progress)
        summary["approved_domains_added"] = _persist_hosts(db, job.id, "official URLs of design systems under identity review")
        db.commit()
        jobsvc.finish(db, job.id, "succeeded", result=summary, records_extracted=summary["processed"])


def run_storybook_job(job: Job) -> None:
    from ..services import storybook
    with SessionLocal() as db:
        def progress(n: int, total: int, msg: str) -> None:
            with SessionLocal() as pdb:
                jobsvc.add_event(pdb, job.id, f"[{n}/{total}] {msg}", phase="projects")
                if jobsvc.heartbeat(pdb, job.id, phase="projects", urls_processed=n, urls_discovered=total):
                    raise RuntimeError("cancelled")
        summary = storybook.run_all(db, progress, refresh=bool((job.params or {}).get("refresh")))
        summary["approved_domains_added"] = _persist_hosts(db, job.id, "published Storybook hosts of showcase projects")
        db.commit()
        n = db.scalar(select(func.count()).select_from(StorybookStory)) or 0
        jobsvc.finish(db, job.id, "succeeded", result=summary, records_extracted=n)


HANDLERS = {"crawl": run_crawl, "build": run_build_job, "export": run_export_job, "review": run_review_job, "storybook": run_storybook_job}


def execute(job_id) -> None:
    with SessionLocal() as db:
        job = db.get(Job, job_id)
        db.expunge(job)
    t0 = time.time()
    try:
        HANDLERS[job.kind](job)
    except Exception as e:  # noqa: BLE001
        log.error("job failed", extra={"job_id": str(job.id)}, exc_info=True)
        with SessionLocal() as db:
            jobsvc.add_event(db, job.id, traceback.format_exc()[-3000:], level="error", phase="error")
            fresh = db.get(Job, job.id)
            if fresh.status == "running":
                if job.kind == "crawl":  # crawls are not auto-retried blindly: errors are usually deterministic; retry is user-driven
                    jobsvc.finish(db, job.id, "failed", error=f"{type(e).__name__}: {e}")
                else:
                    jobsvc.requeue_or_fail(db, fresh, f"{type(e).__name__}: {e}")
    log.info("job done", extra={"job_id": str(job.id), "duration_ms": int((time.time() - t0) * 1000)})


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="drain the queue and exit")
    ap.add_argument("--kinds", default="", help="comma-separated job kinds to process")
    a = ap.parse_args(argv)
    configure_logging()
    s = get_settings()
    from ..services import github_integration
    log.info(f"github client mode: {'authenticated' if github_integration.configure() else 'unauthenticated'}")
    worker_id = f"{socket.gethostname()}:{os.getpid()}"
    kinds = [k for k in a.kinds.split(",") if k] or None
    with session_scope() as db:
        n = jobsvc.recover_stale(db, s.job_heartbeat_timeout_seconds)
        if n:
            log.warning(f"recovered {n} stale job(s)")
    pool = ThreadPoolExecutor(max_workers=s.worker_concurrency)
    running: set = set()
    lock = threading.Lock()
    log.info(f"worker {worker_id} started (concurrency={s.worker_concurrency})")
    idle_since = time.time()
    while True:
        with lock:
            free = s.worker_concurrency - len(running)
        claimed = False
        if free > 0:
            with SessionLocal() as db:
                job = jobsvc.claim(db, worker_id, kinds)
            if job:
                claimed = True
                idle_since = time.time()
                with lock:
                    running.add(job.id)
                fut = pool.submit(execute, job.id)
                fut.add_done_callback(lambda f, jid=job.id: (lock.acquire(), running.discard(jid), lock.release()))
        if a.once and not claimed:
            with lock:
                busy = bool(running)
            if not busy:
                with SessionLocal() as db:
                    waiting = db.scalar(select(Job.id).where(Job.status == "queued").limit(1))
                if not waiting or time.time() - idle_since > 600:
                    break
        if not claimed:
            time.sleep(s.worker_poll_seconds)
    pool.shutdown(wait=True)
    log.info("worker exiting")


if __name__ == "__main__":
    main()
