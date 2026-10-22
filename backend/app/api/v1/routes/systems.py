from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from ....core.exceptions import Conflict, NotFound
from ....database.session import get_db
from ....models import (AttributeEvidence, Component, DesignSystem, DesignToken, EntityCuration, Guideline, Record, Source, StorybookProject,
                        StorybookStory, StorybookVariant, SystemAlias, SystemResource)
from ....repositories import list_components, list_guidelines, list_systems, list_tokens, paginate, system_facets
from ....schemas import (
    AttributeEvidenceOut, ComponentOut, GuidelineOut, Item, Page, ResourceCreate, ResourceOut, ResourceUpdate, SourceOut,
    SystemDetail, SystemOut, SystemUpdate, TokenOut
)
from ....services import resources as ressvc
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


def _alias_target(db: Session, system_id: int) -> tuple[DesignSystem, SystemAlias] | None:
    a = db.scalar(select(SystemAlias).where(SystemAlias.alias_id == system_id))
    seen, key = set(), a.canonical_key if a else None
    while key and key not in seen:
        seen.add(key)
        s = db.scalar(select(DesignSystem).where(DesignSystem.key == key))
        if s:
            return s, a
        nxt = db.get(SystemAlias, key)
        key = nxt.canonical_key if nxt else None
    return None


def primary_links(db: Session, ids: list[int]) -> tuple[dict[int, list[dict]], dict[int, int]]:
    links: dict[int, list[dict]] = {i: [] for i in ids}
    counts: dict[int, int] = {i: 0 for i in ids}
    if not ids:
        return links, counts
    for sid, t, url, st in db.execute(select(SystemResource.system_id, SystemResource.resource_type, SystemResource.url, SystemResource.verification_status)
                                      .where(SystemResource.system_id.in_(ids), SystemResource.is_primary.is_(True))):
        links[sid].append({"type": t, "url": url, "verified": st == "verified"})
    for sid, n in db.execute(select(SystemResource.system_id, func.count()).where(SystemResource.system_id.in_(ids),
                                                                                SystemResource.verification_status != "invalid").group_by(SystemResource.system_id)):
        counts[sid] = n
    for v in links.values():
        v.sort(key=lambda x: ressvc.TYPE_ORDER.index(x["type"]))
    return links, counts


def system_out(s: DesignSystem, links: dict[int, list[dict]], counts: dict[int, int]) -> dict:
    return {**SystemOut.model_validate(s).model_dump(), "links": links.get(s.id, []), "resource_count": counts.get(s.id, 0)}


def _detail(db: Session, s: DesignSystem, requested_alias: SystemAlias | None = None) -> dict:
    links, counts = primary_links(db, [s.id])
    res = db.scalars(select(SystemResource).where(SystemResource.system_id == s.id)
                     .order_by(SystemResource.resource_type, SystemResource.is_primary.desc(), SystemResource.verification_status, SystemResource.id)).all()
    projects = db.scalars(select(StorybookProject).where(StorybookProject.system_key == s.key).order_by(StorybookProject.title)).all()
    from .storybook import P_FIELDS, _d
    pids = [p.id for p in projects]
    stories = db.scalar(select(func.count()).select_from(StorybookStory).where(StorybookStory.project_id.in_(pids))) if pids else 0
    variants = db.scalar(select(func.count()).select_from(StorybookVariant).where(StorybookVariant.project_id.in_(pids))) if pids else 0
    aliases = db.scalars(select(SystemAlias).where(SystemAlias.canonical_key == s.key).order_by(SystemAlias.alias_key)).all()
    return {**SystemDetail.model_validate(s).model_dump(), "links": links.get(s.id, []), "resource_count": counts.get(s.id, 0),
            "resources": [ResourceOut.model_validate(r) for r in res],
            "merged_aliases": [{"key": a.alias_key, "id": a.alias_id, "name": a.alias_name, "reason": a.reason} for a in aliases],
            "requested_alias": {"key": requested_alias.alias_key, "id": requested_alias.alias_id, "name": requested_alias.alias_name} if requested_alias else None,
            "storybook_projects": [_d(p, P_FIELDS) for p in projects], "story_count": stories or 0, "variant_count": variants or 0,
            "guideline_count": db.scalar(select(func.count()).select_from(Guideline).where(Guideline.system_id == s.id)) or 0}


@router.get("", response_model=Page[SystemOut], dependencies=[Depends(require("public:read"))])
def list_(q: str | None = Query(None, max_length=200), framework: list[str] | None = Depends(csv_list("framework")),
          source: list[str] | None = Depends(csv_list("source")), verification: str | None = Query(None, pattern="^(verified|partially_verified|unverified)$"),
          min_sources: int | None = Query(None, ge=1, le=20), has_repo: bool | None = None, has_storybook: bool | None = None,
          platform: list[str] | None = Depends(csv_list("platform")), resource: list[str] | None = Depends(csv_list("resource")),
          verified_resource: list[str] | None = Depends(csv_list("verified_resource")),
          missing_resource: str | None = Query(None, pattern="^(official|official_website|official_documentation|github_repository|figma_file|storybook)$"),
          component: str | None = Query(None, max_length=200, description="systems having a component whose name matches"),
          sort: str | None = Query(None, max_length=30), pp: PageParams = Depends(page_params), db: Session = Depends(get_db)):
    items, total = list_systems(db, q=q, framework=framework, verification=verification, source=source, min_sources=min_sources, has_repo=has_repo,
                                has_storybook=has_storybook, platform=platform, resource=resource, verified_resource=verified_resource,
                                missing_resource=missing_resource, component=component, sort=sort, page=pp.page, page_size=pp.page_size)
    links, counts = primary_links(db, [s.id for s in items])
    return page_out([system_out(s, links, counts) for s in items], total, pp.page, pp.page_size)


@router.get("/facets", dependencies=[Depends(require("public:read"))], summary="Filter facets with counts")
def facets(db: Session = Depends(get_db)):
    return {"data": system_facets(db)}


@router.get("/{system_id}", response_model=Item[SystemDetail], dependencies=[Depends(require("public:read"))])
def get(system_id: int, db: Session = Depends(get_db)):
    s = db.get(DesignSystem, system_id)
    if s:
        return {"data": _detail(db, s)}
    hit = _alias_target(db, system_id)
    if not hit:
        raise NotFound("Design system not found.")
    return {"data": _detail(db, hit[0], hit[1])}


@router.patch("/{system_id}", response_model=Item[SystemDetail], summary="Curator edit of descriptive fields")
def update(system_id: int, body: SystemUpdate, p: Principal = Depends(require("system:write")), db: Session = Depends(get_db)):
    s = _get(db, system_id)
    ch = body.model_dump(exclude_unset=True)
    t = datetime.now(timezone.utc)
    for k, v in ch.items():
        if k == "name" and not v:
            continue
        # Applied immediately and persisted as curation, so the next rebuild re-applies the edit instead of overwriting it.
        setattr(s, k if k != "frameworks" else "frameworks", v)
        ev = [{"type": "admin_edit", "user_id": str(p.id), "at": t.isoformat()}]
        stmt = insert(EntityCuration).values(entity_key=s.key, field=k, value=v, evidence=ev)
        db.execute(stmt.on_conflict_do_update(constraint="uq_entity_curation", set_={"value": v, "evidence": ev}))
    s.attributes = {**(s.attributes or {}), "curated_fields": {**((s.attributes or {}).get("curated_fields") or {}),
                                                              **{k: {"value": v, "evidence": [{"type": "admin_edit"}]} for k, v in ch.items()}}}
    audit(db, p.id, "system.update", "design_system", s.id, changes=ch)
    db.commit()
    db.refresh(s)
    return {"data": _detail(db, s)}


@router.get("/{system_id}/resources", response_model=Page[ResourceOut], dependencies=[Depends(require("public:read"))])
def list_resources(system_id: int, pp: PageParams = Depends(page_params), db: Session = Depends(get_db)):
    _get(db, system_id)
    stmt = select(SystemResource).where(SystemResource.system_id == system_id).order_by(SystemResource.resource_type, SystemResource.is_primary.desc(), SystemResource.id)
    rows, total = paginate(db, stmt, pp.page, pp.page_size)
    return page_out([r[0] for r in rows], total, pp.page, pp.page_size)


@router.post("/{system_id}/resources", response_model=Item[ResourceOut], status_code=201, summary="Add a resource link (administrator)")
def add_resource(system_id: int, body: ResourceCreate, p: Principal = Depends(require("system:write")), db: Session = Depends(get_db)):
    s = _get(db, system_id)
    r = add_manual_resource(db, s.key, s.id, body.resource_type, body.url, label=body.label, verified=body.verification_status == "verified",
                            note=body.evidence_note, user_id=p.id)
    audit(db, p.id, "resource.create", "system_resource", r.id, system=s.key, type=r.resource_type, url=r.url)
    db.commit()
    return {"data": r}


def add_manual_resource(db: Session, key: str, system_id: int | None, rtype: str, url: str, *, label=None, verified=False, note=None, user_id=None) -> SystemResource:
    if rtype == "figma_file" and not ressvc.FIGMA_FILE.match(url):
        raise Conflict("Not a Figma file/community-file URL. Use 'additional_resource' for other figma.com pages.")
    if rtype == "github_repository" and not ressvc.github_repo(url):
        raise Conflict("Not a repository URL (expected https://github.com/<owner>/<repo>).")
    c = ressvc.canon(rtype, url)
    r = db.scalar(select(SystemResource).where(SystemResource.system_key == key, SystemResource.resource_type == rtype, SystemResource.canonical_url == c))
    if r is None:
        r = SystemResource(system_key=key, system_id=system_id, resource_type=rtype, url=url, canonical_url=c, origin="manual", source_keys=["manual"])
        db.add(r)
    r.label = label or r.label
    if verified:
        r.verification_status, r.verification_method = "verified", "admin"
        r.evidence_note = note or "Confirmed by the administrator."
        r.evidence_url = r.evidence_url or url
    db.flush()
    ressvc._choose_primary(db)
    db.refresh(r)
    return r


@router.get("/{system_id}/components", response_model=Page[ComponentOut], dependencies=[Depends(require("public:read"))])
def components(system_id: int, q: str | None = None, pp: PageParams = Depends(page_params), db: Session = Depends(get_db)):
    _get(db, system_id)
    rows, total = list_components(db, q=q, system_id=system_id, page=pp.page, page_size=pp.page_size)
    return page_out([component_out(c, k) for c, k in rows], total, pp.page, pp.page_size)


@router.get("/{system_id}/tokens", response_model=Page[TokenOut], dependencies=[Depends(require("public:read"))])
def tokens(system_id: int, pp: PageParams = Depends(page_params), db: Session = Depends(get_db)):
    _get(db, system_id)
    stmt = select(DesignToken, Source.key).join(Source, Source.id == DesignToken.source_id).where(DesignToken.system_id == system_id).order_by(DesignToken.path)
    rows, total = paginate(db, stmt, pp.page, pp.page_size)
    return page_out([token_out(t, k) for t, k in rows], total, pp.page, pp.page_size)


@router.get("/{system_id}/guidelines", response_model=Page[GuidelineOut], dependencies=[Depends(require("public:read"))])
def guidelines(system_id: int, pp: PageParams = Depends(page_params), db: Session = Depends(get_db)):
    _get(db, system_id)
    stmt = (select(Guideline, Source.key).join(Source, Source.id == Guideline.source_id).where(Guideline.system_id == system_id)
            .order_by(Guideline.category, Guideline.title))
    rows, total = paginate(db, stmt, pp.page, pp.page_size)
    return page_out([guideline_out(g, k) for g, k in rows], total, pp.page, pp.page_size)


@router.get("/{system_id}/sources", dependencies=[Depends(require("public:read"))], summary="Source records that resolved to this system")
def sources(system_id: int, db: Session = Depends(get_db)):
    _get(db, system_id)
    rows = db.execute(select(Record.id, Record.record_key, Record.title, Record.source_url, Record.verification_status, Source.id, Source.key, Source.name)
                      .join(Source, Source.id == Record.source_id).where(Record.system_id == system_id, Record.record_type.in_(["system", "tool"]))
                      .order_by(Source.key).limit(100)).all()
    return {"data": [dict(record_id=a, record_key=b, title=c, evidence_url=d, verification_status=e, source_id=f, source_key=g, source_name=h)
                     for a, b, c, d, e, f, g, h in rows]}


@router.get("/{system_id}/evidence", response_model=Page[AttributeEvidenceOut], dependencies=[Depends(require("public:read"))], summary="Field-level attribute evidence for this system")
def system_evidence(system_id: int, pp: PageParams = Depends(page_params), db: Session = Depends(get_db)):
    sys = _get(db, system_id)
    stmt = select(AttributeEvidence).where(
        (AttributeEvidence.system_id == system_id) | (AttributeEvidence.system_key == sys.key)
    ).order_by(AttributeEvidence.attribute_path, AttributeEvidence.id)
    rows, total = paginate(db, stmt, pp.page, pp.page_size)
    return page_out([r[0] for r in rows], total, pp.page, pp.page_size)


@router.get("/{system_id}/storybook", dependencies=[Depends(require("public:read"))], summary="Storybook showcase project for this system")
def system_storybook(system_id: int, db: Session = Depends(get_db)):
    sys = _get(db, system_id)
    proj = db.scalar(select(StorybookProject).where(StorybookProject.system_key == sys.key))
    if not proj and sys.storybook_url:
        proj = db.scalar(select(StorybookProject).where(StorybookProject.storybook_url == sys.storybook_url))
    if not proj:
        return {"data": None}
    from .storybook import P_FIELDS, _d
    return {"data": _d(proj, P_FIELDS)}



resource_router = APIRouter(prefix="/resources", tags=["design-systems"], responses=ERRORS)


@resource_router.get("", response_model=Page[ResourceOut], dependencies=[Depends(require("public:read"))], summary="All resource links (filterable)")
def all_resources(resource_type: list[str] | None = Depends(csv_list("resource_type")),
                  status: str | None = Query(None, pattern="^(verified|unverified|invalid)$"), origin: str | None = Query(None, max_length=30),
                  q: str | None = Query(None, max_length=200), pp: PageParams = Depends(page_params), db: Session = Depends(get_db)):
    stmt = select(SystemResource).where(SystemResource.system_id.is_not(None))
    if resource_type:
        stmt = stmt.where(SystemResource.resource_type.in_(resource_type))
    if status:
        stmt = stmt.where(SystemResource.verification_status == status)
    if origin:
        stmt = stmt.where(SystemResource.origin == origin)
    if q:
        stmt = stmt.where(SystemResource.url.ilike(f"%{q.replace('%', '').replace('_', '')}%"))
    rows, total = paginate(db, stmt.order_by(SystemResource.system_id, SystemResource.resource_type, SystemResource.id), pp.page, pp.page_size)
    return page_out([r[0] for r in rows], total, pp.page, pp.page_size)


@resource_router.patch("/{resource_id}", response_model=Item[ResourceOut], summary="Correct, confirm, or flag a resource link")
def update_resource(resource_id: int, body: ResourceUpdate, p: Principal = Depends(require("system:write")), db: Session = Depends(get_db)):
    r = db.get(SystemResource, resource_id)
    if not r:
        raise NotFound("Resource not found.")
    ch = body.model_dump(exclude_unset=True)
    if "url" in ch and ch["url"] and ch["url"] != r.url:
        if r.origin != "manual":
            raise Conflict("Only administrator-added links can be re-pointed; add a corrected link and flag this one invalid instead.")
        r.url, r.canonical_url = ch["url"], ressvc.canon(r.resource_type, ch["url"])
    if "label" in ch:
        r.label = ch["label"]
    if ch.get("verification_status"):
        r.verification_status, r.verification_method = ch["verification_status"], "admin"
        r.evidence_note = ch.get("evidence_note") or {"verified": "Confirmed by the administrator.", "invalid": "Flagged invalid by the administrator.",
                                                       "unverified": "Verification withdrawn by the administrator."}[ch["verification_status"]]
    elif "evidence_note" in ch:
        r.evidence_note = ch["evidence_note"]
    if ch.get("is_primary"):
        db.execute(SystemResource.__table__.update().where(SystemResource.system_key == r.system_key, SystemResource.resource_type == r.resource_type)
                   .values(is_primary=False))
        r.is_primary = True
    elif ch.get("verification_status"):
        db.flush()
        ressvc._choose_primary(db)
    audit(db, p.id, "resource.update", "system_resource", r.id, changes=ch)
    db.commit()
    db.refresh(r)
    return {"data": r}


@resource_router.delete("/{resource_id}", status_code=204, summary="Remove an administrator-added link")
def delete_resource(resource_id: int, p: Principal = Depends(require("system:write")), db: Session = Depends(get_db)):
    r = db.get(SystemResource, resource_id)
    if not r:
        raise NotFound("Resource not found.")
    if r.origin != "manual":
        raise Conflict("Links derived from sources are kept for provenance; flag them invalid instead.")
    audit(db, p.id, "resource.delete", "system_resource", r.id, url=r.url)
    db.delete(r)
    db.flush()
    ressvc._choose_primary(db)
    db.commit()
    return Response(status_code=204)
