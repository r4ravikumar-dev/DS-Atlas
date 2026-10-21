from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ....database.session import get_db
from ....models import DiscoveredUrl
from ....repositories import list_jobs, list_sources, paginate
from ....schemas import (CoverageOut, DiscoveredUrlOut, Item, JobAccepted, JobOut, Page, SourceCreate, SourceDetail, SourceOut, SourceUpdate)
from ....services import jobs as jobsvc
from ....services import sources as srcsvc
from ....services.audit import audit
from ...deps import PageParams, Principal, page_params, require
from ..common import ERRORS, page_out

router = APIRouter(prefix="/sources", tags=["sources"], responses=ERRORS)


@router.get("", response_model=Page[SourceOut], dependencies=[Depends(require("read"))])
def list_(q: str | None = Query(None, max_length=200), status_: str | None = Query(None, alias="status"), source_type: str | None = None,
          origin: str | None = Query(None, pattern="^(seed|user)$"), sort: str | None = Query(None, max_length=40),
          pp: PageParams = Depends(page_params), db: Session = Depends(get_db)):
    items, total = list_sources(db, q=q, status=status_, source_type=source_type, origin=origin, sort=sort, page=pp.page, page_size=pp.page_size)
    return page_out(items, total, pp.page, pp.page_size)


@router.post("", response_model=Item[SourceDetail], status_code=status.HTTP_201_CREATED)
def create(body: SourceCreate, p: Principal = Depends(require("source:create")), db: Session = Depends(get_db)):
    src = srcsvc.create(db, name=body.name, url=str(body.url), source_type=body.source_type, max_pages=body.max_pages, max_depth=body.max_depth)
    audit(db, p.id, "source.create", "source", src.id, url=src.url)
    db.commit()
    return {"data": src}


@router.get("/{source_id}", response_model=Item[SourceDetail], dependencies=[Depends(require("read"))])
def get(source_id: int, db: Session = Depends(get_db)):
    return {"data": srcsvc.get(db, source_id)}


@router.patch("/{source_id}", response_model=Item[SourceDetail])
def update(source_id: int, body: SourceUpdate, p: Principal = Depends(require("source:update")), db: Session = Depends(get_db)):
    src = srcsvc.get(db, source_id)
    changes = body.model_dump(exclude_none=True)
    if "name" in changes:
        src.name = changes["name"]
    if "is_paused" in changes:
        src.is_paused = changes["is_paused"]
    if "crawl_limits" in changes:
        src.crawl_limits = {**(src.crawl_limits or {}), **changes["crawl_limits"]}
    audit(db, p.id, "source.update", "source", src.id, changes=changes)
    db.commit()
    return {"data": src}


@router.get("/{source_id}/coverage", response_model=Item[CoverageOut], dependencies=[Depends(require("read"))])
def coverage(source_id: int, db: Session = Depends(get_db)):
    return {"data": srcsvc.coverage(db, srcsvc.get(db, source_id))}


@router.get("/{source_id}/documents", response_model=Page[DiscoveredUrlOut], dependencies=[Depends(require("read"))],
            summary="Discovered URL queue / fetch history for a source")
def documents(source_id: int, outcome: str | None = None, q: str | None = Query(None, max_length=200), pp: PageParams = Depends(page_params),
              db: Session = Depends(get_db)):
    srcsvc.get(db, source_id)
    stmt = select(DiscoveredUrl).where(DiscoveredUrl.source_id == source_id)
    if outcome:
        stmt = stmt.where(DiscoveredUrl.outcome == outcome)
    if q:
        stmt = stmt.where(DiscoveredUrl.url.ilike(f"%{q}%"))
    rows, total = paginate(db, stmt.order_by(DiscoveredUrl.updated_at.desc(), DiscoveredUrl.id), pp.page, pp.page_size)
    return page_out([r[0] for r in rows], total, pp.page, pp.page_size)


@router.get("/{source_id}/jobs", response_model=Page[JobOut], dependencies=[Depends(require("read"))])
def jobs(source_id: int, pp: PageParams = Depends(page_params), db: Session = Depends(get_db)):
    srcsvc.get(db, source_id)
    items, total = list_jobs(db, kinds=["crawl"], source_id=source_id, page=pp.page, page_size=pp.page_size)
    return page_out([jobsvc.to_out(j) for j in items], total, pp.page, pp.page_size)


@router.post("/{source_id}/crawl", response_model=Item[JobAccepted], status_code=status.HTTP_202_ACCEPTED)
def crawl(source_id: int, rebuild: bool = True, refresh: bool = False, p: Principal = Depends(require("crawl:start")), db: Session = Depends(get_db)):
    src = srcsvc.get(db, source_id)
    if src.is_paused:
        from ....core.exceptions import Conflict
        raise Conflict("Source is paused; resume it before crawling.")
    job = jobsvc.enqueue(db, "crawl", source_id=src.id, params={"refresh": refresh}, created_by=p.id)
    ids = [job.id]
    if rebuild:
        ids.append(jobsvc.enqueue(db, "build", params={"after": [str(job.id)]}, created_by=p.id, priority=200).id)
    audit(db, p.id, "crawl.start", "source", src.id, job_id=str(job.id))
    db.commit()
    return {"data": {"job_ids": ids}}
