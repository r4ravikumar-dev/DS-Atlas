"""Read-side repositories: bounded, indexed, paginated queries. No business rules here."""
from __future__ import annotations

import re
from typing import Any, Sequence

from sqlalchemy import Select, and_, cast, func, literal, or_, select, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from ..models import Component, DesignSystem, DesignToken, Guideline, Job, Record, Source


def ts_query(q: str, any_term: bool = False):
    """Build a prefix-aware tsquery from free text (safe: only word characters survive)."""
    words = re.findall(r"\w+", q.lower())[:8]
    if not words:
        return None
    return func.to_tsquery("english", (" | " if any_term else " & ").join(f"{w}:*" for w in words))


def paginate(db: Session, stmt: Select, page: int, page_size: int) -> tuple[Sequence[Any], int]:
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    rows = db.execute(stmt.limit(page_size).offset((page - 1) * page_size)).all()
    return rows, total


def _sort(stmt: Select, sort: str | None, allowed: dict[str, Any], default: list[Any]) -> Select:
    if not sort:
        return stmt.order_by(*default)
    desc = sort.startswith("-")
    col = allowed.get(sort.lstrip("-"))
    if col is None:
        return stmt.order_by(*default)
    return stmt.order_by(col.desc().nulls_last() if desc else col.asc().nulls_last(), *default)


def _json_contains_any(col, values: list[str]):
    import json
    return or_(*[col.op("@>")(cast(json.dumps([v]), JSONB)) for v in values])


def _text_filter(q: str | None, vector, *name_cols):
    if not q:
        return None
    tq = ts_query(q)
    conds = [col.ilike(f"%{q}%") for col in name_cols]
    if tq is not None:
        conds.append(vector.op("@@")(tq))
    return or_(*conds)


# ───────────────────────────── sources & jobs ─────────────────────────────
def list_sources(db: Session, *, q=None, status=None, source_type=None, origin=None, sort=None, page=1, page_size=25):
    stmt = select(Source)
    if q:
        stmt = stmt.where(or_(Source.name.ilike(f"%{q}%"), Source.url.ilike(f"%{q}%"), Source.key.ilike(f"%{q}%")))
    if status:
        stmt = stmt.where(Source.status == status)
    if source_type:
        stmt = stmt.where(Source.source_type == source_type)
    if origin:
        stmt = stmt.where(Source.origin == origin)
    stmt = _sort(stmt, sort, {"key": Source.key, "name": Source.name, "status": Source.status, "records": Source.records_count,
                              "last_success_at": Source.last_success_at, "errors": Source.error_count}, [Source.key])
    rows, total = paginate(db, stmt, page, page_size)
    return [r[0] for r in rows], total


def list_jobs(db: Session, *, kinds: list[str], status=None, source_id=None, page=1, page_size=25):
    stmt = select(Job).where(Job.kind.in_(kinds))
    if status:
        stmt = stmt.where(Job.status == status)
    if source_id:
        stmt = stmt.where(Job.source_id == source_id)
    stmt = stmt.order_by(Job.created_at.desc())
    rows, total = paginate(db, stmt, page, page_size)
    return [r[0] for r in rows], total


# ───────────────────────────── systems ─────────────────────────────
def list_systems(db: Session, *, q=None, framework=None, verification=None, source=None, min_sources=None, has_repo=None,
                 has_storybook=None, platform=None, resource=None, verified_resource=None, missing_resource=None, component=None,
                 has_components=None, has_tokens=None, sort=None, page=1, page_size=25):
    from ..models import SystemResource
    stmt = select(DesignSystem)

    def has_res(rtypes: list[str], verified: bool = False):
        cond = [SystemResource.system_id == DesignSystem.id, SystemResource.resource_type.in_(rtypes)]
        cond.append(SystemResource.verification_status == "verified" if verified else SystemResource.verification_status != "invalid")
        return select(SystemResource.id).where(*cond).exists()

    for t in resource or []:
        stmt = stmt.where(has_res([t]))
    for t in verified_resource or []:
        stmt = stmt.where(has_res([t], verified=True))
    if missing_resource:
        types = ["official_website", "official_documentation"] if missing_resource == "official" else [missing_resource]
        stmt = stmt.where(~has_res(types))
    if platform:
        stmt = stmt.where(_json_contains_any(DesignSystem.platforms, platform))
    if component:
        pat = f"%{component.replace('%', '').replace('_', '')[:100]}%"
        stmt = stmt.where(select(Component.id).where(Component.system_id == DesignSystem.id, Component.name.ilike(pat)).exists())
    f = _text_filter(q, DesignSystem.search_vector, DesignSystem.name, DesignSystem.organization)
    if f is not None:
        stmt = stmt.where(f)
    if framework:
        stmt = stmt.where(_json_contains_any(DesignSystem.frameworks, framework))
    if verification:
        stmt = stmt.where(DesignSystem.verification_status == verification)
    if source:
        stmt = stmt.where(_json_contains_any(DesignSystem.source_keys, source))
    if min_sources:
        stmt = stmt.where(DesignSystem.source_count >= min_sources)
    if has_repo:
        stmt = stmt.where(DesignSystem.repository_url.is_not(None))
    if has_storybook:
        stmt = stmt.where(DesignSystem.storybook_url.is_not(None))
    if has_components:
        stmt = stmt.where(DesignSystem.component_count > 0)
    if has_tokens:
        stmt = stmt.where(DesignSystem.token_count > 0)
    stmt = _sort(stmt, sort, {"name": DesignSystem.name, "sources": DesignSystem.source_count, "components": DesignSystem.component_count,
                              "tokens": DesignSystem.token_count, "updated": DesignSystem.updated_at}, [DesignSystem.source_count.desc(), DesignSystem.name])
    rows, total = paginate(db, stmt, page, page_size)
    return [r[0] for r in rows], total


def system_facets(db: Session) -> dict[str, list[dict[str, Any]]]:
    fw = db.execute(text("SELECT f, count(*) FROM design_systems, jsonb_array_elements_text(frameworks) f GROUP BY f ORDER BY 2 DESC LIMIT 30")).all()
    src = db.execute(text("SELECT s, count(*) FROM design_systems, jsonb_array_elements_text(source_keys) s GROUP BY s ORDER BY s")).all()
    ver = db.execute(select(DesignSystem.verification_status, func.count()).group_by(DesignSystem.verification_status)).all()
    plat = db.execute(text("SELECT p, count(*) FROM design_systems, jsonb_array_elements_text(platforms) p GROUP BY p ORDER BY 2 DESC LIMIT 30")).all()
    res = db.execute(text("""SELECT resource_type, count(DISTINCT system_id), count(DISTINCT system_id) FILTER (WHERE verification_status = 'verified')
                             FROM system_resources WHERE system_id IS NOT NULL AND verification_status <> 'invalid' GROUP BY 1 ORDER BY 1""")).all()
    return {"frameworks": [{"value": a, "count": b} for a, b in fw], "sources": [{"value": a, "count": b} for a, b in src],
            "verification_status": [{"value": a, "count": b} for a, b in ver], "platforms": [{"value": a, "count": b} for a, b in plat],
            "resources": [{"value": a, "count": b, "verified": c} for a, b, c in res]}


# ───────────────────────────── components ─────────────────────────────
def list_components(db: Session, *, q=None, family=None, library=None, framework=None, detail_level=None, has_keyboard=None,
                    has_props=None, system_id=None, source_key=None, sort=None, page=1, page_size=25):
    stmt = select(Component, Source.key).join(Source, Source.id == Component.source_id)
    if q:
        stmt = stmt.join(Record, Record.id == Component.record_id).where(_text_filter(q, Record.search_vector, Component.name))
    if family:
        stmt = stmt.where(Component.family.in_(family))
    if library:
        stmt = stmt.where(Component.library.in_(library))
    if framework:
        stmt = stmt.where(_json_contains_any(Component.frameworks, framework))
    if detail_level:
        stmt = stmt.where(Component.detail_level.in_(detail_level))
    if has_keyboard:
        stmt = stmt.where(Component.keyboard_count > 0)
    if has_props:
        stmt = stmt.where(Component.props_count > 0)
    if system_id:
        stmt = stmt.where(Component.system_id == system_id)
    if source_key:
        stmt = stmt.where(Source.key.in_(source_key))
    stmt = _sort(stmt, sort, {"name": Component.name, "library": Component.library, "props": Component.props_count, "family": Component.family},
                 [Component.props_count.desc(), Component.name])
    return paginate(db, stmt, page, page_size)


def component_facets(db: Session) -> dict[str, list[dict[str, Any]]]:
    fam = db.execute(select(Component.family, func.count()).where(Component.family.is_not(None)).group_by(Component.family).order_by(func.count().desc())).all()
    lib = db.execute(select(Component.library, func.count()).where(Component.detail_level.in_(["api", "doc"])).group_by(Component.library)
                     .order_by(func.count().desc()).limit(40)).all()
    lvl = db.execute(select(Component.detail_level, func.count()).group_by(Component.detail_level)).all()
    return {"families": [{"value": a, "count": b} for a, b in fam], "libraries": [{"value": a, "count": b} for a, b in lib if a],
            "detail_levels": [{"value": a, "count": b} for a, b in lvl if a]}


# ───────────────────────────── tokens ─────────────────────────────
def list_tokens(db: Session, *, q=None, type_=None, theme=None, platform=None, group=None, system=None, source_key=None, component=None,
                has_alias=None, sort=None, page=1, page_size=25):
    stmt = select(DesignToken, Source.key).join(Source, Source.id == DesignToken.source_id)
    if q:
        stmt = stmt.where(or_(DesignToken.path.ilike(f"%{q}%"), DesignToken.description.ilike(f"%{q}%"), DesignToken.raw_value.ilike(f"%{q}%")))
    for col, vals in ((DesignToken.type, type_), (DesignToken.theme, theme), (DesignToken.platform, platform), (DesignToken.group, group),
                      (DesignToken.design_system_name, system), (DesignToken.component, component), (Source.key, source_key)):
        if vals:
            stmt = stmt.where(col.in_(vals))
    if has_alias:
        stmt = stmt.where(DesignToken.alias_of.is_not(None))
    stmt = _sort(stmt, sort, {"path": DesignToken.path, "type": DesignToken.type, "system": DesignToken.design_system_name}, [DesignToken.design_system_name, DesignToken.path])
    return paginate(db, stmt, page, page_size)


def token_facets(db: Session) -> dict[str, list[dict[str, Any]]]:
    def f(col, limit=40):
        return [{"value": a, "count": b} for a, b in db.execute(select(col, func.count()).where(col.is_not(None)).group_by(col).order_by(func.count().desc()).limit(limit)).all()]
    return {"types": f(DesignToken.type), "themes": f(DesignToken.theme), "platforms": f(DesignToken.platform), "groups": f(DesignToken.group, 60),
            "systems": f(DesignToken.design_system_name, 80)}


# ───────────────────────────── guidelines ─────────────────────────────
def list_guidelines(db: Session, *, record_types: list[str], q=None, category=None, kind=None, source_key=None, system=None, priority=None,
                    verification=None, review_status=None, sort=None, page=1, page_size=25):
    stmt = select(Guideline, Source.key).join(Source, Source.id == Guideline.source_id).where(Guideline.record_type.in_(record_types))
    if q:
        stmt = stmt.join(Record, Record.id == Guideline.record_id).where(_text_filter(q, Record.search_vector, Guideline.title))
    for col, vals in ((Guideline.category, category), (Guideline.kind, kind), (Source.key, source_key), (Guideline.design_system_name, system),
                      (Guideline.priority, priority), (Guideline.verification_status, verification), (Guideline.review_status, review_status)):
        if vals:
            stmt = stmt.where(col.in_(vals))
    stmt = _sort(stmt, sort, {"title": Guideline.title, "category": Guideline.category}, [Guideline.category, Guideline.title])
    return paginate(db, stmt, page, page_size)


def guideline_facets(db: Session, record_types: list[str]) -> dict[str, list[dict[str, Any]]]:
    base = Guideline.record_type.in_(record_types)
    cat = db.execute(select(Guideline.category, func.count()).where(base).group_by(Guideline.category).order_by(Guideline.category)).all()
    kind = db.execute(select(Guideline.kind, func.count()).where(base, Guideline.kind.is_not(None)).group_by(Guideline.kind).order_by(func.count().desc())).all()
    src = db.execute(select(Source.key, func.count()).select_from(Guideline).join(Source, Source.id == Guideline.source_id).where(base).group_by(Source.key).order_by(Source.key)).all()
    return {"categories": [{"value": a, "count": b} for a, b in cat], "kinds": [{"value": a, "count": b} for a, b in kind],
            "sources": [{"value": a, "count": b} for a, b in src]}
