"""Daily synchronization: schedule, run orchestration, finalize and reporting.

Schedule
  One persisted row (`sync_schedule`, id=1) holds `next_run_at` (UTC). `tick()` — called by every worker loop iteration and
  by the Vercel cron endpoint — claims a due run with `SELECT … FOR UPDATE SKIP LOCKED` and advances `next_run_at` in the
  same transaction; a partial unique index allows only one `running` run. So any number of worker instances, restarts or
  cron calls start at most one run per period, and manual runs are refused while another run is in progress.

Run
  1. snapshot counts; 2. queue a conditional re-crawl (ETag / Last-Modified → 304 keeps cached content) of every enabled
  source, skipping sources already being crawled; 3. `sync_finalize` (worker job, waits for the crawls) retries transient
  failures once after a backoff, then 4. rebuilds the canonical dataset **only if some source's content changed** (ingest
  fingerprints decide that), and 5. stores metrics computed from what actually happened.

Unchanged sources therefore produce no content writes at all: only operational fields (last checked, job rows, run log).
"""
from __future__ import annotations

import copy
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from ..core.exceptions import Conflict, NotFound
from ..models import (Component, DesignSystem, DesignToken, DuplicateGroup, Guideline, Job, Source, StorybookStory, StorybookVariant,
                      SyncRun, SyncSchedule, SystemResource)
from . import jobs as jobsvc

log = logging.getLogger("app.sync")
RETRY_DELAY = timedelta(minutes=10)
MAX_ATTEMPTS = 2
STALE_RUN_AFTER = timedelta(hours=8)


def now() -> datetime:
    return datetime.now(timezone.utc)


def next_slot(after: datetime, hour: int, minute: int, interval_hours: int = 24) -> datetime:
    """First hour:minute UTC slot strictly after `after` (interval 24 h = daily; other intervals step from that anchor)."""
    after = after.astimezone(timezone.utc)
    anchor = after.replace(hour=hour, minute=minute, second=0, microsecond=0)
    step = timedelta(hours=max(1, interval_hours))
    while anchor <= after:
        anchor += step
    while anchor - step > after:
        anchor -= step
    return anchor


def schedule(db: Session, *, lock: bool = False) -> SyncSchedule:
    q = select(SyncSchedule).where(SyncSchedule.id == 1)
    if lock:
        q = q.with_for_update(skip_locked=True)
    s = db.scalar(q)
    if s is None and not lock:
        s = SyncSchedule(id=1, enabled=True, interval_hours=24, hour_utc=3, minute_utc=0)
        s.next_run_at = next_slot(now(), 3, 0)
        db.add(s)
        db.flush()
    return s


def counts(db: Session) -> dict[str, int]:
    c = lambda m, *w: db.scalar(select(func.count()).select_from(m).where(*w)) or 0  # noqa: E731
    return {"systems": c(DesignSystem), "components": c(Component), "tokens": c(DesignToken),
            "guidelines": c(Guideline, Guideline.record_type.in_(("guideline", "specification"))), "patterns": c(Guideline, Guideline.record_type == "pattern"),
            "stories": c(StorybookStory), "variants": c(StorybookVariant), "resources": c(SystemResource, SystemResource.system_id.is_not(None)),
            "duplicate_candidates": c(DuplicateGroup, DuplicateGroup.review_status == "open", DuplicateGroup.kind == "possible_duplicate_system")}


def running(db: Session) -> SyncRun | None:
    return db.scalar(select(SyncRun).where(SyncRun.status == "running"))


def start_run(db: Session, trigger: str, *, user_id=None, scheduled_for: datetime | None = None, source_ids: list[int] | None = None,
              attempt: int = 1) -> SyncRun:
    """Create a run and queue its crawls + finalize. Raises Conflict while another run is in progress."""
    if running(db):
        raise Conflict("A synchronization run is already in progress.")
    run = SyncRun(id=uuid.uuid4(), trigger=trigger, status="running", scheduled_for=scheduled_for, created_by=user_id, attempt=attempt,
                  metrics={"before": counts(db)})
    db.add(run)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise Conflict("A synchronization run is already in progress.") from None
    q = select(Source).where(Source.is_paused.is_(False)).order_by(Source.key)
    if source_ids:
        q = q.where(Source.id.in_(source_ids))
    per_source, crawl_ids = [], []
    for src in db.scalars(q):
        try:
            j = jobsvc.enqueue(db, "crawl", source_id=src.id, created_by=user_id, priority=120,
                               params={"refresh": True, "sync_run_id": str(run.id), "attempt": 1, "reason": f"{trigger} sync"})
            crawl_ids.append(str(j.id))
            per_source.append({"source_id": src.id, "key": src.key, "name": src.name, "job_ids": [str(j.id)], "outcome": "queued"})
        except Conflict:
            per_source.append({"source_id": src.id, "key": src.key, "name": src.name, "job_ids": [], "outcome": "skipped",
                               "reason": "a crawl of this source was already in progress"})
    run.sources = per_source
    jobsvc.enqueue(db, "sync_finalize", priority=300, created_by=user_id,
                   params={"sync_run_id": str(run.id), "after": crawl_ids, "attempt": 1})
    sch = schedule(db)
    sch.last_run_id = run.id
    run.next_run_at = sch.next_run_at
    db.flush()
    log.info("sync run started", extra={"sync_run_id": str(run.id), "trigger": trigger, "sources": len(crawl_ids)})
    return run


def tick(db: Session, *, at: datetime | None = None) -> SyncRun | None:
    """Heartbeat + claim a due scheduled run (safe to call from many processes). Also marks abandoned runs interrupted."""
    t = at or now()
    _recover(db, t)
    sch = schedule(db, lock=True)
    if sch is None:  # another process holds the row right now
        return None
    sch.last_heartbeat_at = t
    if not sch.enabled or sch.next_run_at is None or sch.next_run_at > t or running(db):
        if sch.next_run_at is None:
            sch.next_run_at = next_slot(t, sch.hour_utc, sch.minute_utc, sch.interval_hours)
        db.flush()
        return None
    due = sch.next_run_at
    sch.next_run_at = next_slot(t, sch.hour_utc, sch.minute_utc, sch.interval_hours)  # advance before starting: never double-claims
    db.flush()
    try:
        return start_run(db, "scheduled", scheduled_for=due)
    except Conflict:
        return None


def _recover(db: Session, t: datetime) -> None:
    r = running(db)
    if r and r.started_at < t - STALE_RUN_AFTER:
        active = db.scalar(select(func.count()).select_from(Job).where(Job.status.in_(jobsvc.ACTIVE),
                                                                         Job.params["sync_run_id"].astext == str(r.id))) or 0
        if not active:
            r.status, r.finished_at = "interrupted", t
            r.errors = [*(r.errors or []), {"error": "run had no active jobs for > 8 h (worker stopped?); marked interrupted"}]
            db.flush()


def finalize(db: Session, run_id: str, attempt: int, progress=None) -> dict[str, Any] | None:
    """Called by the `sync_finalize` job once this attempt's crawls are done. Returns None if it re-queued itself for a retry."""
    run = db.get(SyncRun, uuid.UUID(run_id))
    if run is None or run.status != "running":
        return {"skipped": "run not running"}
    sources = copy.deepcopy(run.sources or [])  # never mutate the loaded JSON in place (the change would not be detected)
    retry_ids = []
    for s in sources:
        if not s["job_ids"]:
            continue
        job = db.get(Job, uuid.UUID(s["job_ids"][-1]))
        src = db.get(Source, s["source_id"])
        res = (job.result or {}) if job else {}
        s.update(job_status=job.status if job else "missing", attempts=len(s["job_ids"]),
                 records_seen=res.get("records_seen"), records_created=res.get("records_created", 0), records_updated=res.get("records_updated", 0),
                 records_unchanged=res.get("records_unchanged", 0), records_marked_stale=res.get("records_marked_stale", 0),
                 stale_suppressed=res.get("stale_suppressed", 0), content_changed=bool(res.get("content_changed")),
                 error=(job.error if job and job.status == "failed" else None))
        if job and job.status == "failed":
            s["outcome"] = "failed"
            s["records_preserved"] = src.records_count if src else None
            transient = not any(x in (job.error or "") for x in ("source no longer exists", "source is paused", "cancelled"))
            if transient and len(s["job_ids"]) < MAX_ATTEMPTS:
                try:
                    j = jobsvc.enqueue(db, "crawl", source_id=s["source_id"], priority=120,
                                       params={"refresh": True, "sync_run_id": run_id, "attempt": len(s["job_ids"]) + 1, "reason": "sync retry"})
                    j.run_after = now() + RETRY_DELAY
                    s["job_ids"].append(str(j.id))
                    s["outcome"] = "retrying"
                    retry_ids.append(str(j.id))
                except Conflict:
                    pass
        elif job and job.status == "cancelled":
            s["outcome"] = "cancelled"
        else:
            s["outcome"] = "changed" if s["content_changed"] else "unchanged"
            s["partial"] = bool(job and job.status == "partially_succeeded")
    run.sources = sources
    flag_modified(run, "sources")
    if retry_ids:
        jobsvc.enqueue(db, "sync_finalize", priority=300, params={"sync_run_id": run_id, "after": retry_ids, "attempt": attempt + 1})
        db.flush()
        return None

    changed = [s for s in sources if s.get("outcome") == "changed"]
    build_summary = None
    if changed:
        if progress:
            progress("building")
        from .build import run_build
        build_summary = run_build(db, None)
        run.built = True
    after = counts(db)
    before = (run.metrics or {}).get("before") or {}
    ch = (build_summary or {}).get("changes", {})
    sm = lambda k: sum((s.get(k) or 0) for s in sources)  # noqa: E731
    checked = [s for s in sources if s.get("outcome") in ("changed", "unchanged", "failed", "cancelled")]
    failed = [s for s in sources if s.get("outcome") in ("failed", "cancelled")]
    metrics = {
        "before": before, "after": after,
        "sources_total": len(sources), "sources_checked": len(checked), "sources_changed": len(changed),
        "sources_unchanged": sum(1 for s in sources if s.get("outcome") == "unchanged"), "sources_failed": len(failed),
        "sources_skipped": sum(1 for s in sources if s.get("outcome") == "skipped"),
        "records_created": sm("records_created"), "records_updated": sm("records_updated"), "records_unchanged": sm("records_unchanged"),
        "records_marked_stale": sm("records_marked_stale"), "records_preserved_on_failure": sum((s.get("records_preserved") or 0) for s in failed),
        "stale_suppressed": sm("stale_suppressed"),
        "new_systems": (ch.get("systems") or {}).get("created", 0), "systems_updated": (ch.get("systems") or {}).get("updated", 0),
        "new_components": (ch.get("components") or {}).get("created", 0), "components_updated": (ch.get("components") or {}).get("updated", 0),
        "new_tokens": (ch.get("tokens") or {}).get("created", 0), "tokens_updated": (ch.get("tokens") or {}).get("updated", 0),
        "new_guidelines": (ch.get("guidelines") or {}).get("created", 0), "guidelines_updated": (ch.get("guidelines") or {}).get("updated", 0),
        "new_stories": max(0, after.get("stories", 0) - before.get("stories", 0)),
        "new_variants": max(0, after.get("variants", 0) - before.get("variants", 0)),
        "duplicate_candidates": after.get("duplicate_candidates", 0),
        "new_duplicate_candidates": max(0, after.get("duplicate_candidates", 0) - before.get("duplicate_candidates", 0)),
        "rebuilt": bool(changed),
    }
    run.metrics = metrics
    run.errors = [{"source": s["key"], "error": s.get("error")} for s in failed]
    total = len([s for s in sources if s.get("outcome") != "skipped"])
    partial = [s for s in sources if s.get("partial")]
    metrics["sources_partial"] = len(partial)
    run.status = ("failed" if total and len(failed) == total else "partially_succeeded" if failed or partial else "succeeded")
    run.finished_at = now()
    run.next_run_at = schedule(db).next_run_at
    db.flush()
    log.info("sync run finished", extra={"sync_run_id": run_id, "status": run.status, "changed": len(changed), "failed": len(failed)})
    return metrics


def to_out(r: SyncRun) -> dict[str, Any]:
    return {"id": r.id, "trigger": r.trigger, "status": r.status, "scheduled_for": r.scheduled_for, "started_at": r.started_at,
            "finished_at": r.finished_at, "attempt": r.attempt, "built": r.built, "metrics": r.metrics or {}, "sources": r.sources or [],
            "errors": r.errors or [], "next_run_at": r.next_run_at}


def get_run(db: Session, run_id: uuid.UUID) -> SyncRun:
    r = db.get(SyncRun, run_id)
    if not r:
        raise NotFound("Sync run not found.")
    return r


def status(db: Session) -> dict[str, Any]:
    sch = schedule(db)
    last = db.scalar(select(SyncRun).where(SyncRun.status != "running").order_by(SyncRun.started_at.desc()).limit(1))
    last_ok = db.scalar(select(SyncRun).where(SyncRun.status.in_(("succeeded", "partially_succeeded"))).order_by(SyncRun.started_at.desc()).limit(1))
    cur = running(db)
    hb = sch.last_heartbeat_at
    return {"enabled": sch.enabled, "interval_hours": sch.interval_hours, "hour_utc": sch.hour_utc, "minute_utc": sch.minute_utc, "timezone": "UTC",
            "next_run_at": sch.next_run_at, "last_heartbeat_at": hb,
            "scheduler_alive": bool(hb and hb > now() - timedelta(minutes=10)),
            "current_run": to_out(cur) if cur else None, "last_run": to_out(last) if last else None,
            "last_successful_run_at": last_ok.finished_at if last_ok else None}


def update_schedule(db: Session, *, enabled: bool | None = None, hour_utc: int | None = None, minute_utc: int | None = None) -> SyncSchedule:
    sch = schedule(db)
    if enabled is not None:
        sch.enabled = enabled
    if hour_utc is not None:
        sch.hour_utc = hour_utc
    if minute_utc is not None:
        sch.minute_utc = minute_utc
    sch.next_run_at = next_slot(now(), sch.hour_utc, sch.minute_utc, sch.interval_hours)
    db.flush()
    return sch

