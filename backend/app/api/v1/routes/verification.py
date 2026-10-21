"""Official-documentation verification: priority selection, registration and field-level evidence."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ....core.exceptions import NotFound
from ....database.session import get_db
from ....models import AttributeEvidence, DesignSystem, Source
from ....repositories import paginate
from ....services import jobs as jobsvc
from ....services import official_docs, settings_service
from ....services.audit import audit
from ...deps import PageParams, Principal, page_params, require
from ..common import ERRORS, page_out

router = APIRouter(prefix="/verification", tags=["verification"], responses=ERRORS)


@router.get("/priority", dependencies=[Depends(require("read"))], summary="Most-cited systems ranked for official-docs verification")
def priority(limit: int = Query(15, ge=1, le=50), db: Session = Depends(get_db)):
    return {"data": official_docs.priority_table(db, limit)}


@router.post("/official-docs", status_code=status.HTTP_202_ACCEPTED, summary="Register top-N official docs sources, approve their domains, queue crawls + build")
def start(limit: int = Query(15, ge=1, le=50), max_pages: int = Query(45, ge=5, le=300), p: Principal = Depends(require("crawl:start")),
          db: Session = Depends(get_db)):
    table = official_docs.priority_table(db, limit)
    srcs = official_docs.register(db, table, max_pages)
    cfg = settings_service.get_config(db)
    known = set(cfg["approved_domains"])
    new = sorted({s.domain for s in srcs} - known)
    if new:
        settings_service.update_config(db, {"approved_domains": sorted(known | set(new))}, p.id)
        audit(db, p.id, "config.approve_domains", "config", None, reason="official documentation of selected design systems", domains=new)
    ids = []
    for s in srcs:
        try:
            ids.append(jobsvc.enqueue(db, "crawl", source_id=s.id, created_by=p.id).id)
        except Exception:  # already active
            pass
    if ids:
        ids.append(jobsvc.enqueue(db, "build", params={"after": [str(i) for i in ids]}, created_by=p.id, priority=200).id)
    audit(db, p.id, "verification.official_docs", "sources", None, systems=[r["system_key"] for r in table])
    db.commit()
    return {"data": {"job_ids": ids, "sources": [{"id": s.id, "key": s.key, "system_key": s.system_key, "url": s.url} for s in srcs]}}


@router.get("/attributes", dependencies=[Depends(require("read"))], summary="Field-level attribute evidence")
def attributes(system_id: int | None = None, attribute: str | None = Query(None, max_length=120), status_: str | None = Query(None, alias="status"),
               pp: PageParams = Depends(page_params), db: Session = Depends(get_db)):
    stmt = select(AttributeEvidence)
    if system_id:
        stmt = stmt.where(AttributeEvidence.system_id == system_id)
    if attribute:
        stmt = stmt.where(AttributeEvidence.attribute_path.like(f"{attribute}%"))
    if status_:
        stmt = stmt.where(AttributeEvidence.verification_status == status_)
    rows, total = paginate(db, stmt.order_by(AttributeEvidence.attribute_path, AttributeEvidence.id), pp.page, pp.page_size)
    return page_out([{"id": a.id, "system_id": a.system_id, "system_key": a.system_key, "attribute_path": a.attribute_path, "value": a.value,
                      "source_url": a.source_url, "source_section": a.source_section, "source_version": a.source_version, "excerpt": a.excerpt,
                      "verification_status": a.verification_status, "method": a.method, "checked_at": a.checked_at} for (a,) in rows],
                    total, pp.page, pp.page_size)
