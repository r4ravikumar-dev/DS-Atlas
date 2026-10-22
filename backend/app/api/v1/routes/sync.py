"""Daily synchronization: admin monitoring/control, content-change history, and the Vercel Cron entry point."""
from __future__ import annotations

import hmac
import uuid

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ....core.config import get_settings
from ....core.exceptions import NotFound, Unauthorized
from ....database.session import get_db
from ....models import RecordChange, SyncRun
from ....repositories import paginate
from ....services import sync as syncsvc
from ....services.audit import audit
from ...deps import PageParams, Principal, page_params, require
from ..common import ERRORS, page_out

router = APIRouter(tags=["sync"], responses=ERRORS)


class ScheduleUpdate(BaseModel):
    enabled: bool | None = None
    hour_utc: int | None = Field(None, ge=0, le=23)
    minute_utc: int | None = Field(None, ge=0, le=59)


@router.get("/admin/sync", dependencies=[Depends(require("admin:config"))], summary="Scheduler state, current and last run")
def sync_status(db: Session = Depends(get_db)):
    out = syncsvc.status(db)
    db.commit()
    return {"data": out}


@router.patch("/admin/sync/schedule", summary="Enable/disable the daily run or change its UTC time")
def update_schedule(body: ScheduleUpdate, p: Principal = Depends(require("admin:config")), db: Session = Depends(get_db)):
    sch = syncsvc.update_schedule(db, **body.model_dump(exclude_none=True))
    audit(db, p.id, "sync.schedule_update", "sync_schedule", None, changes=body.model_dump(exclude_none=True), next_run_at=sch.next_run_at.isoformat())
    db.commit()
    return {"data": syncsvc.status(db)}


@router.post("/admin/sync/run", status_code=202, summary="Start a manual synchronization run now")
def run_now(p: Principal = Depends(require("crawl:start")), db: Session = Depends(get_db)):
    run = syncsvc.start_run(db, "manual", user_id=p.id)
    audit(db, p.id, "sync.run_manual", "sync_run", None, sync_run_id=str(run.id))
    db.commit()
    return {"data": syncsvc.to_out(run)}


@router.get("/admin/sync/runs", dependencies=[Depends(require("admin:config"))], summary="Run history")
def runs(pp: PageParams = Depends(page_params), db: Session = Depends(get_db)):
    rows, total = paginate(db, select(SyncRun).order_by(SyncRun.started_at.desc()), pp.page, pp.page_size)
    return page_out([{**syncsvc.to_out(r[0]), "sources": None} for r in rows], total, pp.page, pp.page_size)


@router.get("/admin/sync/runs/{run_id}", dependencies=[Depends(require("admin:config"))], summary="One run with per-source outcomes")
def run_detail(run_id: uuid.UUID, db: Session = Depends(get_db)):
    return {"data": syncsvc.to_out(syncsvc.get_run(db, run_id))}


@router.get("/admin/changes", dependencies=[Depends(require("admin:config"))], summary="Content-change history (created/updated/staled/restored records)")
def changes(sync_run_id: uuid.UUID | None = None, source_id: int | None = None, change: str | None = Query(None, pattern="^(created|updated|staled|restored)$"),
            pp: PageParams = Depends(page_params), db: Session = Depends(get_db)):
    stmt = select(RecordChange)
    if sync_run_id:
        stmt = stmt.where(RecordChange.sync_run_id == sync_run_id)
    if source_id:
        stmt = stmt.where(RecordChange.source_id == source_id)
    if change:
        stmt = stmt.where(RecordChange.change == change)
    rows, total = paginate(db, stmt.order_by(RecordChange.at.desc(), RecordChange.id.desc()), pp.page, pp.page_size)
    return page_out([{"id": r.id, "sync_run_id": r.sync_run_id, "job_id": r.job_id, "source_id": r.source_id, "record_key": r.record_key,
                      "record_type": r.record_type, "change": r.change, "title": r.title, "at": r.at} for (r,) in rows], total, pp.page, pp.page_size)


@router.get("/internal/cron/sync", include_in_schema=False)
def cron(request: Request, db: Session = Depends(get_db)):
    """Vercel Cron entry point. Vercel sends `Authorization: Bearer $CRON_SECRET`. Claims the run only if it is due, so it
    coexists with the worker's own scheduler loop (whichever ticks first starts the run; the other finds nothing to do)."""
    secret = get_settings().cron_secret
    if not secret:
        raise NotFound("Not found.")
    if not hmac.compare_digest(request.headers.get("authorization", ""), f"Bearer {secret.get_secret_value()}"):
        raise Unauthorized("Invalid cron credentials.")
    run = syncsvc.tick(db)
    db.commit()
    return {"data": {"started": bool(run), "sync_run_id": str(run.id) if run else None, "next_run_at": syncsvc.schedule(db).next_run_at}}
