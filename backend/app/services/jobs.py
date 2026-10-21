"""Durable PostgreSQL-backed job queue.

State machine:  queued → running → (succeeded | partially_succeeded | failed | cancelled)
                failed (attempts < max_attempts, transient) → queued (with backoff)
Claiming uses `FOR UPDATE SKIP LOCKED`, so several worker processes can poll safely.
Running jobs heartbeat; jobs whose heartbeat expires are re-queued on worker start-up (crash recovery)."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from ..core.exceptions import Conflict, NotFound
from ..models import Job, JobEvent, Source

TERMINAL = {"succeeded", "partially_succeeded", "failed", "cancelled"}
ACTIVE = {"queued", "running"}


def now() -> datetime:
    return datetime.now(timezone.utc)


def enqueue(db: Session, kind: str, *, source_id: int | None = None, params: dict[str, Any] | None = None,
            created_by=None, priority: int = 100, retry_of=None) -> Job:
    if kind == "crawl" and source_id is not None:
        existing = db.scalar(select(Job).where(Job.kind == "crawl", Job.source_id == source_id, Job.status.in_(ACTIVE)))
        if existing:
            raise Conflict(f"A crawl for this source is already {existing.status} (job {existing.id}).",
                           details=[{"field": "source_id", "reason": str(existing.id)}])
    job = Job(kind=kind, source_id=source_id, params=params or {}, created_by=created_by, priority=priority, retry_of=retry_of)
    db.add(job)
    db.flush()
    add_event(db, job.id, f"Job queued ({kind})", phase="queued")
    return job


def add_event(db: Session, job_id, message: str, *, level: str = "info", phase: str | None = None, data: dict | None = None) -> None:
    db.add(JobEvent(job_id=job_id, message=message[:4000], level=level, phase=phase, data=data or {}))


def claim(db: Session, worker_id: str, kinds: list[str] | None = None) -> Job | None:
    kind_sql = "AND kind = ANY(:kinds)" if kinds else ""
    row = db.execute(text(f"""
        UPDATE jobs SET status='running', locked_by=:w, heartbeat_at=now(), started_at=COALESCE(started_at, now()),
               attempts = attempts + 1, phase='starting', updated_at=now()
        WHERE id = (SELECT id FROM jobs WHERE status='queued' AND run_after <= now() AND NOT cancel_requested {kind_sql}
                    ORDER BY priority, created_at FOR UPDATE SKIP LOCKED LIMIT 1)
        RETURNING id"""), {"w": worker_id, "kinds": kinds}).first()
    if not row:
        db.commit()
        return None
    db.commit()
    job = db.get(Job, row[0])
    return job


def heartbeat(db: Session, job_id, **counters: Any) -> bool:
    """Persist progress; returns True if cancellation was requested."""
    vals = {k: v for k, v in counters.items() if v is not None}
    db.execute(update(Job).where(Job.id == job_id).values(heartbeat_at=now(), **vals))
    db.commit()
    return bool(db.scalar(select(Job.cancel_requested).where(Job.id == job_id)))


def finish(db: Session, job_id, status: str, *, error: str | None = None, result: dict | None = None, **counters: Any) -> None:
    assert status in TERMINAL
    vals: dict[str, Any] = dict(status=status, finished_at=now(), locked_by=None, phase=status, error=error)
    if result is not None:
        vals["result"] = result
    vals.update({k: v for k, v in counters.items() if v is not None})
    db.execute(update(Job).where(Job.id == job_id).values(**vals))
    add_event(db, job_id, f"Job {status}" + (f": {error}" if error else ""), level="error" if status == "failed" else "info", phase=status)
    db.commit()


def requeue_or_fail(db: Session, job: Job, error: str) -> None:
    if job.attempts < job.max_attempts:
        delay = 30 * (2 ** (job.attempts - 1))
        db.execute(update(Job).where(Job.id == job.id).values(status="queued", locked_by=None, error=error, phase="retry_scheduled",
                                                             run_after=now() + timedelta(seconds=delay)))
        add_event(db, job.id, f"Attempt {job.attempts} failed; retrying in {delay}s: {error}", level="warning", phase="retry_scheduled")
        db.commit()
    else:
        finish(db, job.id, "failed", error=error)


def recover_stale(db: Session, timeout_s: int) -> int:
    cutoff = now() - timedelta(seconds=timeout_s)
    jobs = db.scalars(select(Job).where(Job.status == "running", Job.heartbeat_at < cutoff)).all()
    for j in jobs:
        requeue_or_fail(db, j, f"worker heartbeat lost (locked_by={j.locked_by})")
    return len(jobs)


def get(db: Session, job_id: uuid.UUID) -> Job:
    job = db.get(Job, job_id)
    if not job:
        raise NotFound("Job not found.")
    return job


def cancel(db: Session, job_id: uuid.UUID) -> Job:
    job = get(db, job_id)
    if job.status in TERMINAL:
        raise Conflict(f"Job is already {job.status}.")
    if job.status == "queued":
        job.status, job.finished_at, job.phase = "cancelled", now(), "cancelled"
        add_event(db, job.id, "Cancelled before start", phase="cancelled")
    else:
        job.cancel_requested = True
        add_event(db, job.id, "Cancellation requested; the worker will stop at the next checkpoint", phase=job.phase)
    db.flush()
    return job


def retry(db: Session, job_id: uuid.UUID, user_id) -> Job:
    job = get(db, job_id)
    if job.status not in ("failed", "partially_succeeded", "cancelled"):
        raise Conflict("Only failed, partially succeeded or cancelled jobs can be retried.")
    return enqueue(db, job.kind, source_id=job.source_id, params=job.params, created_by=user_id, retry_of=job.id)


def to_out(job: Job) -> dict[str, Any]:
    d = {c: getattr(job, c) for c in ("id", "kind", "status", "phase", "source_id", "params", "attempts", "urls_discovered", "urls_processed",
                                      "records_extracted", "error_count", "error", "cancel_requested", "retry_of", "created_at", "started_at",
                                      "finished_at", "result")}
    src: Source | None = job.source
    d["source_key"] = src.key if src else None
    d["source_name"] = src.name if src else None
    return d
