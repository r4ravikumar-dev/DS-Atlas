from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ....core.exceptions import NotFound
from ....database.session import get_db
from ....models import Evidence, Guideline, Record, Source
from ....repositories import guideline_facets, list_guidelines
from ....schemas import GuidelineDetail, GuidelineOut, Item, Page
from ...deps import PageParams, page_params, require
from ..common import ERRORS, csv_list, page_out
from ..serializers import guideline_out

router = APIRouter(tags=["guidelines"], responses=ERRORS, dependencies=[Depends(require("public:read"))])
GUIDE_TYPES, PATTERN_TYPES = ["guideline", "specification"], ["pattern"]


def _list(types, q, category, kind, source, system, priority, verification, review_status, sort, pp, db):
    rows, total = list_guidelines(db, record_types=types, q=q, category=category, kind=kind, source_key=source, system=system, priority=priority,
                                  verification=verification, review_status=review_status, sort=sort, page=pp.page, page_size=pp.page_size)
    return page_out([guideline_out(g, k) for g, k in rows], total, pp.page, pp.page_size)


def _detail(db: Session, gid: int, types):
    row = db.execute(select(Guideline, Source.key, Record).join(Source, Source.id == Guideline.source_id).join(Record, Record.id == Guideline.record_id)
                     .where(Guideline.id == gid, Guideline.record_type.in_(types))).first()
    if not row:
        raise NotFound("Not found.")
    g, key, rec = row
    d = guideline_out(g, key)
    d.update(record_key=rec.record_key, source_url=rec.source_url, content=rec.content or {},
             evidence=db.scalars(select(Evidence).where(Evidence.record_id == rec.id).limit(20)).all())
    return {"data": d}


Filters = dict


@router.get("/guidelines", response_model=Page[GuidelineOut])
def list_guidelines_(q: str | None = Query(None, max_length=200), category: list[str] | None = Depends(csv_list("category")),
                     kind: list[str] | None = Depends(csv_list("kind")), source: list[str] | None = Depends(csv_list("source")),
                     system: list[str] | None = Depends(csv_list("system")), priority: list[str] | None = Depends(csv_list("priority")),
                     verification: list[str] | None = Depends(csv_list("verification")), review_status: list[str] | None = Depends(csv_list("review_status")),
                     sort: str | None = None, pp: PageParams = Depends(page_params), db: Session = Depends(get_db)):
    return _list(GUIDE_TYPES, q, category, kind, source, system, priority, verification, review_status, sort, pp, db)


@router.get("/guidelines/facets")
def guideline_facets_(db: Session = Depends(get_db)):
    return {"data": guideline_facets(db, GUIDE_TYPES)}


@router.get("/guidelines/{guideline_id}", response_model=Item[GuidelineDetail])
def get_guideline(guideline_id: int, db: Session = Depends(get_db)):
    return _detail(db, guideline_id, GUIDE_TYPES)


@router.get("/patterns", response_model=Page[GuidelineOut])
def list_patterns(q: str | None = Query(None, max_length=200), category: list[str] | None = Depends(csv_list("category")),
                  source: list[str] | None = Depends(csv_list("source")), sort: str | None = None, pp: PageParams = Depends(page_params), db: Session = Depends(get_db)):
    return _list(PATTERN_TYPES, q, category, None, source, None, None, None, None, sort, pp, db)


@router.get("/patterns/{pattern_id}", response_model=Item[GuidelineDetail])
def get_pattern(pattern_id: int, db: Session = Depends(get_db)):
    return _detail(db, pattern_id, PATTERN_TYPES)


@router.get("/pattern-library/systems", summary="Design systems that publish their own patterns/guidance, with counts")
def pattern_library_systems(db: Session = Depends(get_db)):
    from ....models import DesignSystem
    from ....services.assets import public_assets
    rows = db.execute(select(DesignSystem.id, DesignSystem.slug, DesignSystem.name, DesignSystem.organization, func.count(Guideline.id))
                      .join(Guideline, Guideline.system_id == DesignSystem.id).group_by(DesignSystem.id)
                      .order_by(func.count(Guideline.id).desc(), DesignSystem.name)).all()
    vis = public_assets(db, [r[0] for r in rows])
    return {"data": [{"id": i, "slug": s, "name": n, "organization": o, "count": c, "logo": vis.get(i, {}).get("icon")} for i, s, n, o, c in rows]}


@router.get("/pattern-library/research", response_model=Page[GuidelineOut], summary="Cross-system research patterns, specifications and checklists (not owned by one system)")
def pattern_library_research(q: str | None = Query(None, max_length=200), category: list[str] | None = Depends(csv_list("category")),
                             kind: list[str] | None = Depends(csv_list("kind")), pp: PageParams = Depends(page_params), db: Session = Depends(get_db)):
    from ....repositories import paginate
    stmt = select(Guideline, Source.key).join(Source, Source.id == Guideline.source_id).where(Guideline.system_id.is_(None))
    if q:
        stmt = stmt.where(Guideline.title.ilike(f"%{q.replace('%', '')}%") | Guideline.summary.ilike(f"%{q.replace('%', '')}%"))
    if category:
        stmt = stmt.where(Guideline.category.in_(category))
    if kind:
        stmt = stmt.where(Guideline.kind.in_(kind))
    rows, total = paginate(db, stmt.order_by(Guideline.category, Guideline.title), pp.page, pp.page_size)
    return page_out([guideline_out(g, k) for g, k in rows], total, pp.page, pp.page_size)


@router.get("/pattern-library/facets", summary="Topics and kinds of cross-system research guidance")
def pattern_library_facets(db: Session = Depends(get_db)):
    from ....scrapers.dskb.sources import TAXONOMY
    def count(col):
        return db.execute(select(col, func.count()).where(Guideline.system_id.is_(None), col.is_not(None)).group_by(col).order_by(func.count().desc())).all()
    return {"data": {"categories": [{"value": c, "label": TAXONOMY.get(c, {}).get("name", c), "count": n} for c, n in count(Guideline.category)],
                     "kinds": [{"value": k, "count": n} for k, n in count(Guideline.kind)]}}
