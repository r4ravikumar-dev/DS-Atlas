"""Knowledge-base build: cross-source normalization, categorization, entity resolution and projection.

Input: all non-stale `records`. Output (one transaction, idempotent):
  design_systems (upsert by key; stable ids), components/component_props, design_tokens/token_references,
  guidelines, entity_relationships, duplicate_groups (review status preserved), records.system_id/duplicate_group_key,
  plus generated research/comparison reports."""
from __future__ import annotations

import logging
import re
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from ..models import (Component, ComponentProp, DesignSystem, DesignToken, DiscoveredUrl, DuplicateGroup, EntityRelationship, Guideline,
                      Record, Report, Source, TokenReference)
from ..scrapers.dskb import pipeline as engine
from ..scrapers.dskb import reports as engine_reports
from ..scrapers.dskb.sources import SEEDS, TAXONOMY

log = logging.getLogger("app.build")


def record_to_engine(r: Record, source_key: str) -> dict[str, Any]:
    ex = r.extra or {}
    return {
        "schema_version": ex.get("schema_version", "1.0.0"), "record_id": r.record_key, "record_type": r.record_type, "title": r.title,
        "summary": r.summary, "primary_category": r.primary_category, "secondary_categories": list(r.secondary_categories or []),
        "tags": list(r.tags or []), "organization": r.organization, "design_system": r.design_system_name, "source_id": source_key,
        "source_url": r.source_url, "canonical_url": ex.get("canonical_url"), "repository_url": ex.get("repository_url"),
        "source_file_path": ex.get("source_file_path"), "source_section": ex.get("source_section"), "source_version": r.source_version,
        "source_status": r.source_status, "extraction_method": r.extraction_method, "evidence_excerpt": ex.get("evidence_excerpt"),
        "normalized_content": dict(r.content or {}), "frameworks": list(r.frameworks or []), "platforms": list(ex.get("platforms") or []),
        "technologies": list(r.technologies or []), "license": r.license, "confidence": r.confidence, "verification_status": r.verification_status,
        "last_verified_at": r.last_verified_at.isoformat() if r.last_verified_at else None,
        "relationships": [x for x in (ex.get("relationships") or []) if x.get("type") != "canonical_entity"],
        "duplicate_group_id": None, "notes": list(ex.get("notes") or []), "_db_id": r.id,
    }


def load_engine_records(db: Session) -> tuple[list[dict[str, Any]], dict[int, str]]:
    keys = dict(db.execute(select(Source.id, Source.key)).all())
    out = [record_to_engine(r, keys[r.source_id]) for r in db.scalars(select(Record).where(Record.is_stale.is_(False)).order_by(Record.id))]
    return out, keys


def _s(v, n=None):
    if v is None:
        return None
    s = v if isinstance(v, str) else str(v)
    return s[:n] if n else s


def run_build(db: Session, job_id=None, progress=None) -> dict[str, Any]:
    _SRC_CACHE.clear()
    db.execute(text("SET LOCAL statement_timeout = 0"))
    db.execute(text("SELECT pg_advisory_xact_lock(424242)"))  # one build at a time
    records, keys = load_engine_records(db)
    if progress:
        progress("normalizing", len(records))
    engine.normalize(records)
    engine.categorize(records)
    entities, review = engine.dedupe_systems(records)
    from . import identity
    entities, merged = identity.apply(db, entities)
    review = _remap_review(review, merged)
    review += engine.dedupe_other(records)
    validation = engine.validate(records, entities)
    now = datetime.now(timezone.utc)
    by_key = {r["record_id"]: r for r in records}
    rid = {r["record_id"]: r["_db_id"] for r in records}

    # ── design systems (stable ids by key) ──
    if progress:
        progress("projecting_systems", len(entities))
    existing = dict(db.execute(select(DesignSystem.key, DesignSystem.id)).all())
    keep = set()
    for e in entities:
        desc = next((by_key[k]["summary"] for k in e["source_record_ids"] if by_key.get(k, {}).get("summary") and by_key[k]["record_type"] == "system"), None)
        vals = dict(name=_s(e["name"], 300), organization=_s(e["organization"], 300), description=desc, documentation_url=e.get("documentation_url"),
                    repository_url=e.get("repository_url"), storybook_url=e.get("storybook_url"), design_resource_url=e.get("design_resource_url"),
                    frameworks=e.get("supported_frameworks") or [], platforms=e.get("supported_platforms") or [], styling_strategy=e.get("styling_strategy"),
                    token_architecture=e.get("token_architecture"), accessibility_documentation=e.get("accessibility_documentation"),
                    governance=e.get("governance_documentation"), ai_readiness=e.get("ai_readiness"), source_count=e["source_count"],
                    source_keys=e["sources"], verification_status=e["verification_status"], verification_basis=e.get("verification_basis"),
                    conflicts=e.get("conflicts") or {}, aliases=e.get("aliases") or [], deprecated=bool(e.get("deprecated_flag")),
                    official_docs_url=e.get("official_docs_url"), related_urls=(e.get("related_urls") or [])[:50],
                    verification_coverage=e.get("verification_coverage") or {},
                    attributes={"documentation_coverage": e.get("documentation_coverage"), "framework_evidence": e.get("framework_evidence"),
                                "ai_ready_signals": e.get("ai_ready_signals"), "evidence_urls": e.get("evidence_urls", [])[:20],
                                "source_record_keys": e["source_record_ids"][:200], "related_systems": e.get("related_systems") or [],
                                "merged_from": e.get("merged_from") or [], "curated_fields": e.get("curated_fields") or {},
                                "organization_aliases": e.get("organization_aliases") or []},
                    last_verified_at=now)
        stmt = insert(DesignSystem).values(key=e["system_id"], **vals)
        db.execute(stmt.on_conflict_do_update(index_elements=["key"], set_={**vals, "updated_at": now}))
        keep.add(e["system_id"])
    stale_keys = [k for k in existing if k not in keep]
    if stale_keys:
        db.execute(delete(DesignSystem).where(DesignSystem.key.in_(stale_keys)))
    sys_ids = dict(db.execute(select(DesignSystem.key, DesignSystem.id)).all())
    # attach field-level evidence to (possibly merged) canonical systems
    db.execute(text("UPDATE attribute_evidence SET system_id = NULL"))
    db.execute(text("""UPDATE attribute_evidence a SET system_id = d.id FROM design_systems d WHERE d.key = a.system_key"""))
    for frm, to in merged.items():
        if sys_ids.get(to):
            db.execute(text("UPDATE attribute_evidence SET system_id = :sid WHERE system_key = :k"), {"sid": sys_ids[to], "k": frm})

    # ── record → system / duplicate group ──
    rec_sys: dict[int, int | None] = {}
    for e in entities:
        for k in e["source_record_ids"]:
            if k in rid:
                rec_sys[rid[k]] = sys_ids.get(e["system_id"])
    db.execute(update(Record).values(system_id=None, duplicate_group_key=None))
    lib_entity = {}  # official library sources (S11–S16): every record of the source belongs to the library entity
    for r in records:
        if r["record_type"] == "tool" and (r["normalized_content"] or {}).get("kind") == "component_library" and rec_sys.get(r["_db_id"]):
            lib_entity[r["source_id"]] = rec_sys[r["_db_id"]]
    for r in records:
        sid = rec_sys.get(r["_db_id"]) or (sys_ids.get(r.get("system_entity")) if r.get("system_entity") else None)
        if not sid:
            for rel in r.get("relationships") or []:
                if rel.get("type") in ("documented_by_system", "token_of", "part_of", "foundation_of") and rid.get(rel.get("target")):
                    sid = rec_sys.get(rid[rel["target"]])
                    if sid:
                        break
        if not sid and r["source_id"] in lib_entity:
            sid = lib_entity[r["source_id"]]
        r["_system_db_id"] = sid
    _bulk_update_records(db, [{"id": r["_db_id"], "system_id": r["_system_db_id"], "dup": r.get("duplicate_group_id")} for r in records])

    # ── components ──
    if progress:
        progress("projecting_components", sum(1 for r in records if r["record_type"] == "component"))
    db.execute(delete(ComponentProp))
    comp_keep = []
    for r in records:
        if r["record_type"] != "component":
            continue
        nc = r["normalized_content"]
        vals = dict(name=_s(nc.get("component_name") or r["title"], 300), family=nc.get("family"), library=_s(nc.get("library") or r.get("design_system"), 300),
                    system_id=r["_system_db_id"], source_id=_source_id(db, r["source_id"]), detail_level=nc.get("detail_level"), kind=nc.get("component_kind"),
                    description=r.get("summary"), documentation_url=nc.get("documentation_url"), props_count=int(nc.get("props_count") or 0),
                    keyboard_count=len(nc.get("keyboard") or []), a11y_count=len(nc.get("accessibility_notes") or []), frameworks=r.get("frameworks") or [],
                    verification_status=r["verification_status"], source_version=_s(r.get("source_version"), 200))
        stmt = insert(Component).values(record_id=r["_db_id"], **vals)
        cid = db.execute(stmt.on_conflict_do_update(index_elements=["record_id"], set_=vals).returning(Component.id)).scalar_one()
        comp_keep.append(r["_db_id"])
        props = []
        pos = 0
        for sub in nc.get("subcomponents") or []:
            for p in sub.get("props") or []:
                if not p.get("name"):
                    continue
                props.append(dict(component_id=cid, subcomponent=_s(sub.get("name"), 300), name=_s(p.get("name"), 300), type=_s(p.get("type")),
                                  default_value=_s(p.get("default")), description=_s(p.get("description")), required=_s(p.get("required"), 50), position=pos))
                pos += 1
        if props:
            db.execute(insert(ComponentProp), props)
    db.execute(delete(Component).where(Component.record_id.not_in(comp_keep or [-1])))

    # ── tokens ──
    tok_keep = []
    for r in records:
        if r["record_type"] != "token":
            continue
        nc = r["normalized_content"]
        path = _s(nc.get("token_path") or r["title"], 500)
        group = path.split(".")[0] if "." in path else (re.match(r"--[a-z]+-([a-z]+)", path).group(1) if re.match(r"--[a-z]+-([a-z]+)", path) else None)
        vals = dict(name=_s(nc.get("token_name") or r["title"], 300), path=path, group=_s(group, 200), type=_s(nc.get("token_type"), 200),
                    type_inferred=bool(nc.get("type_inferred")), raw_value=_s(nc.get("raw_value")), resolved_value=_s(nc.get("resolved_value")),
                    alias_of=_s(nc.get("alias_of"), 500), theme=_s(nc.get("theme"), 50), platform=_s(nc.get("platform"), 50), component=_s(nc.get("component"), 200),
                    description=_s(nc.get("description")), source_format=_s(nc.get("source_format"), 200), design_system_name=_s(r.get("design_system"), 300),
                    system_id=r["_system_db_id"], source_id=_source_id(db, r["source_id"]), verification_status=r["verification_status"],
                    source_version=_s(r.get("source_version"), 200))
        stmt = insert(DesignToken).values(record_id=r["_db_id"], **vals)
        db.execute(stmt.on_conflict_do_update(index_elements=["record_id"], set_=vals))
        tok_keep.append(r["_db_id"])
    db.execute(delete(DesignToken).where(DesignToken.record_id.not_in(tok_keep or [-1])))
    refs = _token_references(db)

    # ── guidelines / patterns / specifications ──
    g_keep = []
    for r in records:
        if r["record_type"] not in ("guideline", "pattern", "specification"):
            continue
        nc = r["normalized_content"]
        vals = dict(record_type=r["record_type"], kind=_s(nc.get("kind"), 60), title=r["title"], category=r["primary_category"], summary=r.get("summary"),
                    section=r.get("source_section"), priority=_s(nc.get("priority"), 20), design_system_name=_s(r.get("design_system"), 300),
                    system_id=r["_system_db_id"], source_id=_source_id(db, r["source_id"]), confidence=r["confidence"], verification_status=r["verification_status"])
        stmt = insert(Guideline).values(record_id=r["_db_id"], **vals)
        db.execute(stmt.on_conflict_do_update(index_elements=["record_id"], set_=vals))
        g_keep.append(r["_db_id"])
    db.execute(delete(Guideline).where(Guideline.record_id.not_in(g_keep or [-1])))

    # ── relationships ──
    db.execute(delete(EntityRelationship))
    rels = []
    for r in records:
        for rel in r.get("relationships") or []:
            t = rel.get("target")
            if rel.get("type") == "canonical_entity":
                if sys_ids.get(t):
                    rels.append(dict(from_record_id=r["_db_id"], type="canonical_entity", to_record_id=None, to_system_id=sys_ids[t]))
            elif t in rid:
                rels.append(dict(from_record_id=r["_db_id"], type=rel["type"], to_record_id=rid[t], to_system_id=None))
    for i in range(0, len(rels), 2000):
        db.execute(insert(EntityRelationship), rels[i:i + 2000])

    # ── review queue (preserve human decisions) ──
    open_keys = set()
    for item in review:
        key = item["type"] + ":" + (item.get("entity") or item.get("group") or item.get("organization") or "")
        members = len(item.get("entities") or item.get("records") or []) or 1
        stmt = insert(DuplicateGroup).values(key=key[:400], kind=item["type"], member_count=members, details=item)
        db.execute(stmt.on_conflict_do_update(index_elements=["key"], set_={"details": item, "member_count": members, "updated_at": now}))
        open_keys.add(key[:400])
    db.execute(delete(DuplicateGroup).where(DuplicateGroup.key.not_in(open_keys or {"-"}), DuplicateGroup.review_status == "open"))

    # ── counts on systems ──
    db.execute(text("""UPDATE design_systems d SET
        component_count = (SELECT count(*) FROM components c WHERE c.system_id = d.id),
        token_count = (SELECT count(*) FROM design_tokens t WHERE t.system_id = d.id)"""))

    # ── generated reports (engine analysis over the same canonical dataset) ──
    if progress:
        progress("generating_reports", 0)
    report_ids = _generate_reports(db, records, entities, review, validation, job_id)
    summary = {"records": len(records), "systems": len(entities), "components": len(comp_keep), "tokens": len(tok_keep), "guidelines": len(g_keep),
               "relationships": len(rels), "token_references": refs, "review_items": len(review), "validation_issues": validation["issue_count"],
               "reports": [str(x) for x in report_ids]}
    log.info("build complete", extra={"job_id": str(job_id)})
    return summary


_SRC_CACHE: dict[str, int] = {}


def _source_id(db: Session, key: str) -> int:
    if key not in _SRC_CACHE:
        _SRC_CACHE[key] = db.scalar(select(Source.id).where(Source.key == key))
    return _SRC_CACHE[key]


def _bulk_update_records(db: Session, rows: list[dict[str, Any]]) -> None:
    rows = [r for r in rows if r["system_id"] or r["dup"]]
    for i in range(0, len(rows), 1000):
        chunk = rows[i:i + 1000]
        db.execute(text("""UPDATE records AS r SET system_id = v.system_id, duplicate_group_key = v.dup
                           FROM (SELECT * FROM jsonb_to_recordset(CAST(:rows AS jsonb)) AS x(id bigint, system_id int, dup text)) v
                           WHERE r.id = v.id"""), {"rows": __import__("json").dumps(chunk)})


def _token_references(db: Session) -> int:
    """Resolve aliases (var(--x) / {group.token}) to tokens of the same system/source, preferring the same theme."""
    db.execute(delete(TokenReference))
    toks = db.execute(select(DesignToken.id, DesignToken.name, DesignToken.path, DesignToken.alias_of, DesignToken.theme, DesignToken.source_id,
                             DesignToken.design_system_name)).all()
    index = defaultdict(list)
    for t in toks:
        index[(t.source_id, t.design_system_name, t.name)].append(t)
        index[(t.source_id, t.design_system_name, t.path)].append(t)
    refs = []
    for t in toks:
        if not t.alias_of:
            continue
        cands = index.get((t.source_id, t.design_system_name, t.alias_of)) or []
        cands = [c for c in cands if c.id != t.id]
        if not cands:
            continue
        best = next((c for c in cands if c.theme == t.theme), cands[0])
        refs.append({"token_id": t.id, "references_token_id": best.id})
    uniq = {(r["token_id"], r["references_token_id"]): r for r in refs}
    if uniq:
        db.execute(insert(TokenReference), list(uniq.values()))
        db.execute(text("""UPDATE design_tokens t SET resolved_value = r.raw_value FROM token_references x JOIN design_tokens r ON r.id = x.references_token_id
                           WHERE x.token_id = t.id AND r.alias_of IS NULL"""))
    return len(uniq)


def _coverage_map(db: Session) -> dict[str, dict[str, Any]]:
    from ..scrapers.dskb.adapters.common import new_coverage
    out = {}
    for s in SEEDS:
        src = db.scalar(select(Source).where(Source.key == s["source_id"]))
        cov = new_coverage(s)
        if src:
            cov.update({k: v for k, v in (src.coverage or {}).items() if v is not None})
            cov.update(crawl_status=src.status, http_status=src.http_status, resolved_url=src.resolved_url, page_title=src.page_title,
                       pages_attempted=src.pages_attempted, pages_ok=src.pages_ok, robots=src.robots,
                       completed_at=src.last_attempted_at.isoformat() if src.last_attempted_at else None)
            cov.setdefault("items_found", 0)
            cov["records_emitted"] = src.records_count
        else:
            cov["crawl_status"] = "not_run"
        out[s["source_id"]] = cov
    return out


def _manifest(db: Session) -> list[dict[str, Any]]:
    keys = dict(db.execute(select(Source.id, Source.key)).all())
    return [{"url": u, "source_id": keys.get(sid), "outcome": o, "status": st} for u, sid, o, st in
            db.execute(select(DiscoveredUrl.url, DiscoveredUrl.source_id, DiscoveredUrl.outcome, DiscoveredUrl.http_status))]


def _generate_reports(db: Session, records, entities, review, validation, job_id) -> list:
    coverage = _coverage_map(db)
    manifest = _manifest(db)
    stats = engine.library_stats(records)
    sources = [{"source_id": k, "origin": "seed", **{f: c.get(f) for f in ("name", "crawl_status", "http_status", "pages_attempted", "pages_ok",
                                                                            "items_found", "records_emitted", "limitations")}, "error_count": len(c.get("errors") or [])}
               for k, c in coverage.items()]
    crawl = engine_reports.crawl_report(records, entities, coverage, review, validation, manifest, sources, datetime.now(timezone.utc).isoformat())
    out = []
    for kind, title, md in (
        ("research_report", "Design-systems research report", engine_reports.research_report(records, entities, coverage, stats, crawl, review)),
        ("comparison_report", "Comparative analysis: component libraries & directories", engine_reports.comparison(records, entities, stats)),
        ("knowledge_base_index", "Knowledge base index", engine_reports.kb_index(records, entities, crawl)),
    ):
        rep = Report(kind=kind, title=title, content_md=md, data={"crawl_summary": crawl["summary"]} if kind == "research_report" else {}, job_id=job_id)
        db.add(rep)
        db.flush()
        out.append(rep.id)
    db.add(Report(kind="crawl_report", title="Crawl coverage & error report", content_md="See data.", data=_jsonable(crawl), job_id=job_id))
    db.add(Report(kind="data_quality", title="Data-quality validation", content_md=f"Validation issues: {validation['issue_count']}",
                  data=_jsonable({"validation": validation, "review_by_type": crawl.get("review_queue_by_type")}), job_id=job_id))
    db.flush()
    return out


def _jsonable(o):
    import json
    return json.loads(json.dumps(o, default=str))


def _remap_review(review: list[dict[str, Any]], merged: dict[str, str]) -> list[dict[str, Any]]:
    """Point review items at post-merge entities; drop duplicate-candidate items whose candidates were merged into one."""
    out = []
    for item in review:
        if item.get("entity") in merged:
            item = {**item, "entity": merged[item["entity"]]}
        if item.get("type") == "possible_duplicate_system":
            ents, seen = [], set()
            for e in item.get("entities", []):
                k = merged.get(e["system_id"], e["system_id"])
                if k not in seen:
                    seen.add(k)
                    ents.append({**e, "system_id": k})
            if len(ents) < 2:
                continue
            item = {**item, "entities": ents}
        out.append(item)
    return out
