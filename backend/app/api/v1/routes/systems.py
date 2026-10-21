from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ....core.exceptions import NotFound
from ....database.session import get_db
from ....models import Component, DesignSystem, DesignToken, Guideline, Record, Source
from ....repositories import list_components, list_guidelines, list_systems, list_tokens, paginate, system_facets
from ....schemas import ComponentOut, GuidelineOut, Item, Page, SourceOut, SystemDetail, SystemOut, SystemUpdate, TokenOut
from ....services.audit import audit
from ...deps import PageParams, Principal, page_params, require
from ..common import ERRORS, csv_list, page_out
from ..serializers import component_out, guideline_out, token_out

router = APIRouter(prefix="/design-systems", tags=["design-systems"], responses=ERRORS)


def _get(db: Session, system_id: int) -> DesignSystem:
    s = db.get(DesignSystem, system_id)
    if not s:
        raise NotFound("Design system not found.")
    return s


@router.get("", response_model=Page[SystemOut], dependencies=[Depends(require("read"))])
def list_(q: str | None = Query(None, max_length=200), framework: list[str] | None = Depends(csv_list("framework")),
          source: list[str] | None = Depends(csv_list("source")), verification: str | None = Query(None, pattern="^(verified|partially_verified|unverified)$"),
          min_sources: int | None = Query(None, ge=1, le=20), has_repo: bool | None = None, has_storybook: bool | None = None,
          sort: str | None = Query(None, max_length=30), pp: PageParams = Depends(page_params), db: Session = Depends(get_db)):
    items, total = list_systems(db, q=q, framework=framework, verification=verification, source=source, min_sources=min_sources, has_repo=has_repo,
                                has_storybook=has_storybook, sort=sort, page=pp.page, page_size=pp.page_size)
    return page_out(items, total, pp.page, pp.page_size)


@router.get("/facets", dependencies=[Depends(require("read"))], summary="Filter facets with counts")
def facets(db: Session = Depends(get_db)):
    return {"data": system_facets(db)}


@router.get("/{system_id}", response_model=Item[SystemDetail], dependencies=[Depends(require("read"))])
def get(system_id: int, db: Session = Depends(get_db)):
    return {"data": _get(db, system_id)}


@router.patch("/{system_id}", response_model=Item[SystemDetail], summary="Curator edit of descriptive fields")
def update(system_id: int, body: SystemUpdate, p: Principal = Depends(require("system:write")), db: Session = Depends(get_db)):
    s = _get(db, system_id)
    ch = body.model_dump(exclude_none=True)
    for k, v in ch.items():
        setattr(s, k, v)
    s.attributes = {**(s.attributes or {}), "curator_edited_fields": sorted(set((s.attributes or {}).get("curator_edited_fields", [])) | set(ch))}
    audit(db, p.id, "system.update", "design_system", s.id, changes=ch)
    db.commit()
    return {"data": s}


@router.get("/{system_id}/components", response_model=Page[ComponentOut], dependencies=[Depends(require("read"))])
def components(system_id: int, q: str | None = None, pp: PageParams = Depends(page_params), db: Session = Depends(get_db)):
    _get(db, system_id)
    rows, total = list_components(db, q=q, system_id=system_id, page=pp.page, page_size=pp.page_size)
    return page_out([component_out(c, k) for c, k in rows], total, pp.page, pp.page_size)


@router.get("/{system_id}/tokens", response_model=Page[TokenOut], dependencies=[Depends(require("read"))])
def tokens(system_id: int, pp: PageParams = Depends(page_params), db: Session = Depends(get_db)):
    _get(db, system_id)
    stmt = select(DesignToken, Source.key).join(Source, Source.id == DesignToken.source_id).where(DesignToken.system_id == system_id).order_by(DesignToken.path)
    rows, total = paginate(db, stmt, pp.page, pp.page_size)
    return page_out([token_out(t, k) for t, k in rows], total, pp.page, pp.page_size)


@router.get("/{system_id}/guidelines", response_model=Page[GuidelineOut], dependencies=[Depends(require("read"))])
def guidelines(system_id: int, pp: PageParams = Depends(page_params), db: Session = Depends(get_db)):
    _get(db, system_id)
    stmt = (select(Guideline, Source.key).join(Source, Source.id == Guideline.source_id).where(Guideline.system_id == system_id)
            .order_by(Guideline.category, Guideline.title))
    rows, total = paginate(db, stmt, pp.page, pp.page_size)
    return page_out([guideline_out(g, k) for g, k in rows], total, pp.page, pp.page_size)


@router.get("/{system_id}/sources", dependencies=[Depends(require("read"))], summary="Source records that resolved to this system")
def sources(system_id: int, db: Session = Depends(get_db)):
    _get(db, system_id)
    rows = db.execute(select(Record.id, Record.record_key, Record.title, Record.source_url, Record.verification_status, Source.id, Source.key, Source.name)
                      .join(Source, Source.id == Record.source_id).where(Record.system_id == system_id, Record.record_type.in_(["system", "tool"]))
                      .order_by(Source.key).limit(100)).all()
    return {"data": [dict(record_id=a, record_key=b, title=c, evidence_url=d, verification_status=e, source_id=f, source_key=g, source_name=h)
                     for a, b, c, d, e, f, g, h in rows]}
