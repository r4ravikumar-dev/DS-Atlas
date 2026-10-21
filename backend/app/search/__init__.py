"""Global search over records (all types), canonical systems and sources using PostgreSQL full-text search
with prefix matching, weighted ranking (title > system/org > summary) and ts_headline snippets."""
from __future__ import annotations

from typing import Any

import json

from sqlalchemy import String, cast, func, literal, or_, select, union_all
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from ..models import Component, DesignSystem, DesignToken, Guideline, Record, Source
from ..repositories import ts_query

TYPE_TO_RECORD = {"component": ["component"], "token": ["token"], "guideline": ["guideline", "specification"], "pattern": ["pattern"],
                  "resource": ["resource"], "tool": ["tool", "repository"], "system_listing": ["system"]}
ALL_TYPES = ["system", "source", *TYPE_TO_RECORD]


def search(db: Session, q: str, *, types: list[str] | None, category: list[str] | None, source: list[str] | None,
           technology: list[str] | None, page: int, page_size: int) -> tuple[list[dict[str, Any]], int, dict[str, int]]:
    """All-terms match first; if nothing matches, fall back to any-term matching (ranked by how many terms hit)."""
    hits, total, facets = _search(db, ts_query(q), q, types, category, source, technology, page, page_size)
    if total == 0 and len(q.split()) > 1:
        hits, total, facets = _search(db, ts_query(q, any_term=True), q, types, category, source, technology, page, page_size)
        facets["_match_mode"] = "any"  # type: ignore[assignment]
    return hits, total, facets


def _search(db, tq, q, types, category, source, technology, page, page_size):
    if tq is None:
        return [], 0, {}
    types = types or ALL_TYPES
    parts = []
    rec_types = [rt for t in types for rt in TYPE_TO_RECORD.get(t, [])]
    if rec_types:
        r = (select(Record.record_type.label("type"), cast(Record.id, String).label("id"), Record.title.label("title"),
                    func.coalesce(Record.design_system_name, Record.organization).label("subtitle"),
                    func.ts_headline("english", func.coalesce(Record.summary, Record.title), tq, "MaxWords=28, MinWords=10, ShortWord=2").label("snippet"),
                    Source.key.label("source_key"), Record.primary_category.label("category"),
                    func.ts_rank_cd(Record.search_vector, tq).label("rank"))
             .join(Source, Source.id == Record.source_id)
             .where(Record.search_vector.op("@@")(tq), Record.is_stale.is_(False), Record.record_type.in_(rec_types)))
        if category:
            r = r.where(Record.primary_category.in_(category))
        if source:
            r = r.where(Source.key.in_(source))
        if technology:
            r = r.where(or_(*[Record.frameworks.op("@>")(cast(json.dumps([t]), JSONB)) for t in technology],
                            *[Record.technologies.op("@>")(cast(json.dumps([t]), JSONB)) for t in technology]))
        parts.append(r)
    if "system" in types and not category:
        s = (select(literal("system").label("type"), cast(DesignSystem.id, String).label("id"), DesignSystem.name.label("title"),
                    DesignSystem.organization.label("subtitle"),
                    func.ts_headline("english", func.coalesce(DesignSystem.description, DesignSystem.name), tq, "MaxWords=28, MinWords=10").label("snippet"),
                    literal(None).label("source_key"), literal("C12").label("category"),
                    (func.ts_rank_cd(DesignSystem.search_vector, tq) * 1.5 + DesignSystem.source_count * 0.05).label("rank"))
             .where(DesignSystem.search_vector.op("@@")(tq)))
        if source:
            s = s.where(or_(*[DesignSystem.source_keys.op("@>")(cast(json.dumps([k]), JSONB)) for k in source]))
        parts.append(s)
    if "source" in types and not category and not technology:
        so = (select(literal("source").label("type"), cast(Source.id, String).label("id"), Source.name.label("title"),
                     Source.key.label("subtitle"), Source.url.label("snippet"), Source.key.label("source_key"), literal(None).label("category"),
                     func.ts_rank_cd(Source.search_vector, tq).label("rank"))
              .where(or_(Source.search_vector.op("@@")(tq), Source.name.ilike(f"%{q}%"))))
        if source:
            so = so.where(Source.key.in_(source))
        parts.append(so)
    if not parts:
        return [], 0, {}
    u = union_all(*parts).subquery()
    total = db.scalar(select(func.count()).select_from(u)) or 0
    facets = dict(db.execute(select(u.c.type, func.count()).group_by(u.c.type)).all())
    rows = db.execute(select(u).order_by(u.c.rank.desc(), u.c.title).limit(page_size).offset((page - 1) * page_size)).mappings().all()
    hits = []
    # map record ids to their projection ids for deep links
    rec_ids = [int(r["id"]) for r in rows if r["type"] not in ("system", "source")]
    comp = dict(db.execute(select(Component.record_id, Component.id).where(Component.record_id.in_(rec_ids))).all()) if rec_ids else {}
    tok = dict(db.execute(select(DesignToken.record_id, DesignToken.id).where(DesignToken.record_id.in_(rec_ids))).all()) if rec_ids else {}
    gl = dict(db.execute(select(Guideline.record_id, Guideline.id).where(Guideline.record_id.in_(rec_ids))).all()) if rec_ids else {}
    for r in rows:
        t, rid = r["type"], int(r["id"])
        if t == "system":
            url, out_id = f"/platform/systems/{rid}", rid
        elif t == "source":
            url, out_id = f"/platform/sources/{rid}", rid
        elif t == "component" and rid in comp:
            url, out_id = f"/platform/components/{comp[rid]}", comp[rid]
        elif t == "token" and rid in tok:
            url, out_id = f"/platform/tokens?focus={tok[rid]}", tok[rid]
        elif rid in gl:
            url, out_id = f"/platform/guidelines/{gl[rid]}", gl[rid]
        else:
            url, out_id = f"/platform/records/{rid}", rid
        hits.append({"type": t, "id": str(out_id), "title": r["title"], "subtitle": r["subtitle"], "snippet": r["snippet"], "url": url,
                     "source_key": r["source_key"], "category": r["category"], "rank": float(r["rank"] or 0)})
    return hits, total, facets
