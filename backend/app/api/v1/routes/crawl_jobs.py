from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ....core.exceptions import Conflict
from ....database.session import get_db
from ....models import JobEvent, Source
from ....repositories import list_jobs, paginate
from ....schemas import CrawlRequest, Item, JobAccepted, JobEventOut, JobOut, Page
from ....services import jobs as jobsvc
from ....services.audit import audit
from ...deps import PageParams, Principal, page_params, require
from ..common import ERRORS, page_out

router = APIRouter(prefix="/crawl-jobs", tags=["crawl-jobs"], responses=ERRORS)
KINDS = ["crawl", "build", "review", "storybook", "verify_resources", "sync_finalize"]


@router.get("", response_model=Page[JobOut], dependencies=[Depends(require("read"))])
def list_(status_: str | None = Query(None, alias="status"), kind: str | None = Query(None, pattern="^(crawl|build|review|storybook|verify_resources|sync_finalize)$"), source_id: int | None = None,
          pp: PageParams = Depends(page_params), db: Session = Depends(get_db)):
    items, total = list_jobs(db, kinds=[kind] if kind else KINDS, status=status_, source_id=source_id, page=pp.page, page_size=pp.page_size)
    return page_out([jobsvc.to_out(j) for j in items], total, pp.page, pp.page_size)


@router.post("", response_model=Item[JobAccepted], status_code=status.HTTP_202_ACCEPTED, summary="Queue crawls for several sources (optionally followed by a build)")
def create(body: CrawlRequest, p: Principal = Depends(require("crawl:start")), db: Session = Depends(get_db)):
    q = select(Source).where(Source.is_paused.is_(False))
    if body.source_ids:
        q = q.where(Source.id.in_(body.source_ids))
    ids, skipped = [], []
    for src in db.scalars(q.order_by(Source.key)):
        try:
            ids.append(jobsvc.enqueue(db, "crawl", source_id=src.id, created_by=p.id).id)
        except Conflict:
            skipped.append(src.key)
    if body.rebuild and ids:
        ids.append(jobsvc.enqueue(db, "build", params={"after": [str(i) for i in ids]}, created_by=p.id, priority=200).id)
    if not body.source_ids and not body.rebuild and not ids:
        raise Conflict("Nothing to queue.")
    audit(db, p.id, "crawl.batch", "jobs", None, count=len(ids), skipped=skipped)
    db.commit()
    return {"data": {"job_ids": ids}}


@router.post("/build", response_model=Item[JobAccepted], status_code=status.HTTP_202_ACCEPTED, summary="Queue a knowledge-base rebuild")
def build(p: Principal = Depends(require("crawl:start")), db: Session = Depends(get_db)):
    job = jobsvc.enqueue(db, "build", created_by=p.id, priority=150)
    audit(db, p.id, "build.start", "job", job.id)
    db.commit()
    return {"data": {"job_ids": [job.id]}}


@router.get("/{job_id}", response_model=Item[JobOut], dependencies=[Depends(require("read"))])
def get(job_id: uuid.UUID, db: Session = Depends(get_db)):
    return {"data": jobsvc.to_out(jobsvc.get(db, job_id))}


@router.get("/{job_id}/events", response_model=Page[JobEventOut], dependencies=[Depends(require("read"))])
def events(job_id: uuid.UUID, after_id: int | None = Query(None, ge=0, description="Return only events newer than this id (polling)"),
           pp: PageParams = Depends(page_params), db: Session = Depends(get_db)):
    jobsvc.get(db, job_id)
    stmt = select(JobEvent).where(JobEvent.job_id == job_id)
    if after_id:
        stmt = stmt.where(JobEvent.id > after_id)
    rows, total = paginate(db, stmt.order_by(JobEvent.id), pp.page, pp.page_size)
    return page_out([r[0] for r in rows], total, pp.page, pp.page_size)


@router.post("/{job_id}/cancel", response_model=Item[JobOut])
def cancel(job_id: uuid.UUID, p: Principal = Depends(require("job:cancel")), db: Session = Depends(get_db)):
    job = jobsvc.cancel(db, job_id)
    audit(db, p.id, "job.cancel", "job", job_id)
    db.commit()
    return {"data": jobsvc.to_out(job)}


@router.post("/{job_id}/retry", response_model=Item[JobAccepted], status_code=status.HTTP_202_ACCEPTED)
def retry(job_id: uuid.UUID, p: Principal = Depends(require("job:retry")), db: Session = Depends(get_db)):
    job = jobsvc.retry(db, job_id, p.id)
    audit(db, p.id, "job.retry", "job", job_id, new_job=str(job.id))
    db.commit()
    return {"data": {"job_ids": [job.id]}}
