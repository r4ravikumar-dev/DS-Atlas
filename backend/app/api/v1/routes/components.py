from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ....core.exceptions import NotFound
from ....database.session import get_db
from ....models import Component, ComponentProp, DesignToken, Evidence, Guideline, Record, Source, StorybookStory, StorybookVariant
from ....repositories import component_facets, list_components
from ....schemas import ComponentDetail, ComponentOut, ComponentStorybookOut, EvidenceOut, GuidelineOut, Item, Page, TokenOut
from ...deps import PageParams, page_params, require
from ..common import ERRORS, csv_list, page_out
from ..serializers import component_out, guideline_out, token_out

router = APIRouter(prefix="/components", tags=["components"], responses=ERRORS, dependencies=[Depends(require("public:read"))])


def _get(db: Session, component_id: int) -> tuple[Component, Record, str]:
    row = db.execute(select(Component, Record, Source.key).join(Record, Record.id == Component.record_id).join(Source, Source.id == Component.source_id)
                     .where(Component.id == component_id)).first()
    if not row:
        raise NotFound("Component not found.")
    return row[0], row[1], row[2]


@router.get("", response_model=Page[ComponentOut])
def list_(q: str | None = Query(None, max_length=200), family: list[str] | None = Depends(csv_list("family")),
          library: list[str] | None = Depends(csv_list("library")), framework: list[str] | None = Depends(csv_list("framework")),
          detail_level: list[str] | None = Depends(csv_list("detail_level")), source: list[str] | None = Depends(csv_list("source")),
          has_keyboard: bool | None = None, has_props: bool | None = None, system_id: int | None = None, sort: str | None = Query(None, max_length=30),
          pp: PageParams = Depends(page_params), db: Session = Depends(get_db)):
    rows, total = list_components(db, q=q, family=family, library=library, framework=framework, detail_level=detail_level, has_keyboard=has_keyboard,
                                  has_props=has_props, system_id=system_id, source_key=source, sort=sort, page=pp.page, page_size=pp.page_size)
    return page_out([component_out(c, k) for c, k in rows], total, pp.page, pp.page_size)


@router.get("/facets")
def facets(db: Session = Depends(get_db)):
    return {"data": component_facets(db)}


@router.get("/{component_id}", response_model=Item[ComponentDetail])
def get(component_id: int, db: Session = Depends(get_db)):
    c, rec, key = _get(db, component_id)
    nc = rec.content or {}
    props = db.scalars(select(ComponentProp).where(ComponentProp.component_id == c.id).order_by(ComponentProp.position).limit(1500)).all()
    d = component_out(c, key)
    d.update(record_key=rec.record_key, source_url=rec.source_url, props=props,
             subcomponents=[{"name": s.get("name"), "props_count": len(s.get("props") or []), "data_attributes": (s.get("data_attributes") or [])[:50],
                             "css_variables": (s.get("css_variables") or [])[:50]} for s in (nc.get("subcomponents") or [])][:60],
             keyboard=(nc.get("keyboard") or [])[:100], accessibility_notes=(nc.get("accessibility_notes") or [])[:20], examples=(nc.get("examples") or [])[:60],
             variants=nc.get("variants_from_source"), data_attributes=(nc.get("data_attributes") or [])[:60], css_variables=(nc.get("css_variables") or [])[:60],
             anatomy=nc.get("anatomy"), section_outline=(nc.get("section_outline") or [])[:80], notes=((rec.extra or {}).get("notes") or [])[:10])
    return {"data": d}


@router.get("/{component_id}/evidence", response_model=Page[EvidenceOut])
def evidence(component_id: int, db: Session = Depends(get_db)):
    c, rec, _ = _get(db, component_id)
    ev = db.scalars(select(Evidence).where(Evidence.record_id == rec.id).limit(50)).all()
    return page_out(ev, len(ev), 1, 50)


@router.get("/{component_id}/related-tokens", response_model=Page[TokenOut], summary="Tokens scoped to this component (same library/system)")
def related_tokens(component_id: int, limit: int = Query(50, ge=1, le=100), db: Session = Depends(get_db)):
    c, rec, _ = _get(db, component_id)
    scope = [DesignToken.design_system_name == c.library]
    if c.system_id:
        scope.append(DesignToken.system_id == c.system_id)
    stmt = (select(DesignToken, Source.key).join(Source, Source.id == DesignToken.source_id)
            .where(or_(*scope), func.lower(DesignToken.component) == c.name.lower().replace(" ", "")).limit(limit))
    rows = db.execute(stmt).all()
    return page_out([token_out(t, k) for t, k in rows], len(rows), 1, limit)


@router.get("/{component_id}/related-guidelines", response_model=Page[GuidelineOut])
def related_guidelines(component_id: int, limit: int = Query(25, ge=1, le=100), db: Session = Depends(get_db)):
    c, rec, _ = _get(db, component_id)
    words = [w for w in [c.name, c.family] if w]
    conds = [Guideline.title.ilike(f"%{w}%") for w in words]
    stmt = (select(Guideline, Source.key).join(Source, Source.id == Guideline.source_id).where(or_(*conds))
            .order_by(Guideline.verification_status, Guideline.title).limit(limit))
    rows = db.execute(stmt).all()
    return page_out([guideline_out(g, k) for g, k in rows], len(rows), 1, limit)


@router.get("/{component_id}/related-components", response_model=Page[ComponentOut], summary="Same-family components in other libraries/systems")
def related_components(component_id: int, limit: int = Query(30, ge=1, le=100), only_api: bool = True, db: Session = Depends(get_db)):
    c, rec, _ = _get(db, component_id)
    if not c.family:
        return page_out([], 0, 1, limit)
    stmt = (select(Component, Source.key).join(Source, Source.id == Component.source_id)
            .where(Component.family == c.family, Component.id != c.id))
    if only_api:
        stmt = stmt.where(Component.detail_level.in_(["api", "doc"]))
    rows = db.execute(stmt.order_by(Component.props_count.desc()).limit(limit)).all()
    return page_out([component_out(x, k) for x, k in rows], len(rows), 1, limit)


@router.get("/{component_id}/storybook", response_model=Item[ComponentStorybookOut], summary="Storybook stories and variants linked to this component")
def component_storybook(component_id: int, db: Session = Depends(get_db)):
    c, _, _ = _get(db, component_id)
    from .storybook import S_FIELDS, V_FIELDS, _d
    stories = db.scalars(select(StorybookStory).where(StorybookStory.component_id == c.id).order_by(StorybookStory.title, StorybookStory.name).limit(100)).all()
    variants = db.scalars(select(StorybookVariant).where(StorybookVariant.component_id == c.id).order_by(StorybookVariant.label).limit(200)).all()
    if not stories and c.name:
        stories = db.scalars(select(StorybookStory).where(func.lower(StorybookStory.component_name) == c.name.lower()).order_by(StorybookStory.title).limit(50)).all()
        variants = db.scalars(select(StorybookVariant).where(func.lower(StorybookVariant.component_name) == c.name.lower()).order_by(StorybookVariant.label).limit(100)).all()
    return {"data": {"stories": [_d(s, S_FIELDS) for s in stories], "variants": [_d(v, V_FIELDS) for v in variants]}}

