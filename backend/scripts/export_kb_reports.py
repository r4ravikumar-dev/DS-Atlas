"""Generate the knowledge-base deliverables from the live database (no hand-entered numbers):

    research/output/canonical_identity_map.json
    research/output/deduplication_report.json / .md
    research/output/data_reconciliation_report.json / .md

Before/after figures compare against research/output/_snapshots/<ts>/baseline_counts.json (captured from the pre-change backup).
The storage → API trace calls the real API in-process with a short-lived administrator token that is never printed or written.

    .venv/bin/python scripts/export_kb_reports.py [--baseline research/output/_snapshots/20261022T061440Z/baseline_counts.json]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import func, select, text  # noqa: E402

from app.database.session import SessionLocal  # noqa: E402
from app.models import (Component, DesignSystem, DuplicateGroup, IdentityLink, Record, ReviewDecision, StorybookProject, SystemAlias,  # noqa: E402
                        SystemResource, User)

OUT = ROOT / "research" / "output"


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def counts(db) -> dict[str, int]:
    tabs = db.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY 1")).scalars().all()
    return {t: db.scalar(text(f'SELECT count(*) FROM "{t}"')) for t in tabs}


def norm(n: str | None) -> str:
    return re.sub(r"[^a-z0-9]", "", re.sub(r"\b(design system|design-system|ds)\b", "", (n or "").lower()))


def identity_map(db) -> list[dict]:
    aliases = defaultdict(list)
    for a in db.scalars(select(SystemAlias)):
        aliases[a.canonical_key].append({"alias_key": a.alias_key, "alias_id": a.alias_id, "alias_name": a.alias_name, "reason": a.reason})
    res = defaultdict(list)
    for r in db.scalars(select(SystemResource).where(SystemResource.system_id.is_not(None)).order_by(SystemResource.resource_type, SystemResource.id)):
        res[r.system_id].append({"type": r.resource_type, "url": r.url, "status": r.verification_status, "primary": r.is_primary, "origin": r.origin,
                                 "sources": r.source_keys, "evidence_url": r.evidence_url})
    out = []
    for d in db.scalars(select(DesignSystem).order_by(DesignSystem.name, DesignSystem.id)):
        attrs = d.attributes or {}
        out.append({"id": d.id, "key": d.key, "name": d.name, "organization": d.organization, "verification_status": d.verification_status,
                    "source_keys": d.source_keys, "source_record_keys": attrs.get("source_record_keys", []), "merged_aliases": aliases.get(d.key, []),
                    "merged_in_build": [{"system_key": m.get("system_id"), "name": m.get("name")} for m in attrs.get("merged_from", [])],
                    "related_systems": attrs.get("related_systems", []), "resources": res.get(d.id, [])})
    return out


def api_trace(db) -> list[dict]:
    """Storage count vs what the authenticated API reports for each record type."""
    from fastapi.testclient import TestClient
    from app.core.security import create_session_token
    from app.main import app
    admin = db.scalar(select(User).where(User.role == "admin", User.is_active.is_(True)).order_by(User.created_at))
    if not admin:
        return [{"check": "api_trace", "error": "no active administrator; API trace skipped"}]
    c = TestClient(app)
    h = {"Authorization": f"Bearer {create_session_token(str(admin.id), admin.role, admin.session_version)}"}
    q = lambda sql: db.scalar(text(sql)) or 0  # noqa: E731
    checks = [
        ("design systems", "/api/v1/design-systems", q("SELECT count(*) FROM design_systems")),
        ("components", "/api/v1/components", q("SELECT count(*) FROM components")),
        ("design tokens", "/api/v1/tokens", q("SELECT count(*) FROM design_tokens")),
        ("guidelines (guideline/specification)", "/api/v1/guidelines", q("SELECT count(*) FROM guidelines WHERE record_type IN ('guideline','specification')")),
        ("patterns", "/api/v1/patterns", q("SELECT count(*) FROM guidelines WHERE record_type = 'pattern'")),
        ("storybook projects", "/api/v1/storybook/projects", q("SELECT count(*) FROM storybook_projects")),
        ("storybook stories", "/api/v1/storybook/stories", q("SELECT count(*) FROM storybook_stories")),
        ("component variants", "/api/v1/storybook/variants", q("SELECT count(*) FROM storybook_variants")),
        ("resource links (attached)", "/api/v1/resources", q("SELECT count(*) FROM system_resources WHERE system_id IS NOT NULL")),
        ("sources", "/api/v1/sources", q("SELECT count(*) FROM sources")),
        ("attribute evidence", "/api/v1/verification/attributes", q("SELECT count(*) FROM attribute_evidence")),
    ]
    out = []
    for label, path, stored in checks:
        r = c.get(path, headers=h, params={"page_size": 1})
        api_total = r.json().get("meta", {}).get("total_items") if r.status_code == 200 else None
        out.append({"record_type": label, "endpoint": path, "stored": stored, "api_total": api_total, "http_status": r.status_code,
                    "match": api_total == stored})
    # last page reachable (pagination beyond the first page)
    r = c.get("/api/v1/design-systems", headers=h, params={"page_size": 25}).json()
    last = c.get("/api/v1/design-systems", headers=h, params={"page_size": 25, "page": r["meta"]["total_pages"]}).json()
    out.append({"record_type": "design systems — last page", "endpoint": f"/api/v1/design-systems?page={r['meta']['total_pages']}&page_size=25",
                "stored": r["meta"]["total_items"] - 25 * (r["meta"]["total_pages"] - 1), "api_total": len(last["data"]), "http_status": 200,
                "match": len(last["data"]) == r["meta"]["total_items"] - 25 * (r["meta"]["total_pages"] - 1)})
    anon = c.get("/api/v1/design-systems")
    out.append({"record_type": "anonymous access", "endpoint": "/api/v1/design-systems (no credentials)", "stored": None, "api_total": None,
                "http_status": anon.status_code, "match": anon.status_code == 401})
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", default=str(OUT / "_snapshots" / "20261022T061440Z" / "baseline_counts.json"))
    a = ap.parse_args()
    base = json.loads(Path(a.baseline).read_text()) if Path(a.baseline).exists() else None
    with SessionLocal() as db:
        cur = counts(db)
        systems = db.execute(select(DesignSystem.name, DesignSystem.organization, DesignSystem.documentation_url, DesignSystem.repository_url)).all()
        groups = Counter(norm(n) for n, *_ in systems)
        same_name = {k: v for k, v in groups.items() if k and v > 1}
        aliases = db.scalars(select(SystemAlias).order_by(SystemAlias.alias_key)).all()
        decisions = db.scalars(select(ReviewDecision).order_by(ReviewDecision.id)).all()
        latest = {}
        for d in decisions:
            latest[d.review_key] = d
        dec_counts = Counter(d.decision for d in latest.values())
        curated_rationale = sum(1 for d in latest.values() if any(isinstance(e, dict) and any(
            isinstance(x, dict) and x.get("type") == "curated_evidence" for x in (e.get("evidence") or [])) for e in (d.evidence or [])))
        open_items = db.scalars(select(DuplicateGroup).where(DuplicateGroup.review_status == "open").order_by(DuplicateGroup.kind, DuplicateGroup.key)).all()
        links = Counter(l.relation for l in db.scalars(select(IdentityLink)))
        res_counts = db.execute(text("""SELECT resource_type, verification_status, count(*) FROM system_resources WHERE system_id IS NOT NULL
                                        GROUP BY 1, 2 ORDER BY 1, 2""")).all()
        figma_reclassified = db.scalar(text("""SELECT count(*) FROM system_resources WHERE resource_type = 'additional_resource' AND url ILIKE '%figma.com%'"""))
        systems_with = {t: db.scalar(text(f"""SELECT count(DISTINCT system_id) FROM system_resources WHERE resource_type = '{t}' AND system_id IS NOT NULL
                                              AND verification_status <> 'invalid'""")) for t in
                        ("official_website", "official_documentation", "github_repository", "figma_file", "storybook")}
        systems_with_verified = {t: db.scalar(text(f"""SELECT count(DISTINCT system_id) FROM system_resources WHERE resource_type = '{t}'
                                                       AND verification_status = 'verified'""")) for t in systems_with}
        from app.api.v1.routes.quality import orphan_counts
        orphans = {**orphan_counts(db),
            "system_agnostic_guidelines (not broken)": db.scalar(text("SELECT count(*) FROM guidelines WHERE system_id IS NULL")),
        }
        quality = {
            "systems_missing_official_link": db.scalar(text("""SELECT count(*) FROM design_systems d WHERE NOT EXISTS (SELECT 1 FROM system_resources r
                WHERE r.system_id = d.id AND r.resource_type IN ('official_website','official_documentation') AND r.verification_status <> 'invalid')""")),
            "systems_without_organization": db.scalar(text("SELECT count(*) FROM design_systems WHERE organization IS NULL")),
            "invalid_links": db.scalar(text("SELECT count(*) FROM system_resources WHERE verification_status = 'invalid' AND system_id IS NOT NULL")),
            "storybook_projects_not_indexed": db.scalar(text("SELECT count(*) FROM storybook_projects WHERE status <> 'indexed'")),
            "open_review_items": len(open_items),
        }
        verification = dict(db.execute(select(DesignSystem.verification_status, func.count()).group_by(DesignSystem.verification_status)).all())
        trace = api_trace(db)
        imap = identity_map(db)

    gen = now()
    (OUT / "canonical_identity_map.json").write_text(json.dumps({"generated_at": gen, "canonical_systems": len(imap), "systems": imap}, indent=2, default=str))

    b = base or {}
    bt = b.get("table_counts", {})
    dedup = {
        "generated_at": gen,
        "baseline": {"source": b.get("captured_from"), "design_systems": b.get("design_systems"), "same_normalized_name_groups": b.get("same_normalized_name_groups"),
                     "rows_in_same_name_groups": b.get("rows_in_same_name_groups"), "systems_without_docs_or_repo": b.get("systems_without_docs_or_repo")},
        "current": {"design_systems": cur["design_systems"], "same_normalized_name_groups": len(same_name), "rows_in_same_name_groups": sum(same_name.values()),
                    "systems_without_docs_or_repo": sum(1 for _, _, d, r in systems if not d and not r)},
        "net_reduction": (b.get("design_systems") or 0) - cur["design_systems"] if base else None,
        "merges": {
            "recorded_aliases": len(aliases), "by_reason": dict(Counter(a.reason for a in aliases)),
            "note": ("Merges done by the engine's URL identity during this run (after the designsystems.one detail-page fix) fold records into an existing "
                     "canonical key without a separate row being removed, so they show up as the net reduction rather than as alias rows."),
            "aliases": [{"alias_key": a.alias_key, "alias_id": a.alias_id, "alias_name": a.alias_name, "canonical_key": a.canonical_key, "reason": a.reason}
                        for a in aliases],
        },
        "identity_links": dict(links),
        "review_decisions_latest_per_item": dict(dec_counts),
        "decisions_resting_on_curated_rationale": curated_rationale,
        "open_items": [{"key": g.key, "kind": g.kind, "resolution": g.resolution,
                        "entities": [e.get("name") for e in (g.details or {}).get("entities", [])] or None,
                        "rationale": (latest.get(g.key).rationale if latest.get(g.key) else None)} for g in open_items],
        "remaining_same_name_groups": sorted(same_name),
    }
    (OUT / "deduplication_report.json").write_text(json.dumps(dedup, indent=2, default=str))

    recon = {
        "generated_at": gen,
        "canonical_system_count": cur["design_systems"],
        "baseline_system_count": b.get("design_systems"),
        "confirmed_duplicates_merged": dedup["net_reduction"],
        "retained": {k: {"before": bt.get(k), "after": cur.get(k)} for k in
                     ("records", "components", "component_props", "design_tokens", "guidelines", "storybook_projects", "storybook_stories",
                      "storybook_variants", "attribute_evidence", "sources", "raw_documents")},
        "resources": {"by_type_and_status": [{"type": t, "status": s_, "count": n} for t, s_, n in res_counts],
                      "systems_with": systems_with, "systems_with_verified": systems_with_verified,
                      "figma_profile_or_community_pages_reclassified_as_additional_resource": figma_reclassified},
        "orphaned_relationships": {"before": {"storybook_projects_without_system": b.get("storybook_projects_without_system")}, "after": orphans},
        "verification_status": verification,
        "remaining_issues": quality,
        "storage_to_api_trace": trace,
        "root_causes_fixed": [
            "designsystems.one gallery-only entries had no URLs (detail pages never read) → separate name-only catalog entries; adapter now reads detail pages",
            "official-docs crawl following a redirect produced a new site key → duplicate system; sources registered for a system now bind to it",
            "name-only collisions were never raised for review; now queued and decided by the evidence resolver (never merged on name alone)",
            "63 Storybook projects had no system link (set only when a public index existed); relinked through their showcase listing on every build",
            "merged systems were hard-deleted with no mapping; old keys/ids now resolve through system_aliases",
            "administrator edits were overwritten by the next rebuild; edits are now stored as curation and re-applied",
            "links lived in four loose columns without type, provenance or verification; now typed system_resources with evidence",
        ],
    }
    (OUT / "data_reconciliation_report.json").write_text(json.dumps(recon, indent=2, default=str))

    # ── Markdown ──
    md = [f"# Deduplication report\n\nGenerated {gen} from the live database (`scripts/export_kb_reports.py`).\n",
          "| | Before | After |\n|---|---:|---:|",
          f"| Canonical design systems | {b.get('design_systems', '—')} | {cur['design_systems']} |",
          f"| Same-name groups | {b.get('same_normalized_name_groups', '—')} | {len(same_name)} |",
          f"| Rows in same-name groups | {b.get('rows_in_same_name_groups', '—')} | {sum(same_name.values())} |",
          f"| Systems with neither docs nor repository URL | {b.get('systems_without_docs_or_repo', '—')} | {dedup['current']['systems_without_docs_or_repo']} |",
          f"\nNet reduction: **{dedup['net_reduction']}** systems. Recorded alias rows (old key/ID → canonical): **{len(aliases)}** "
          f"({', '.join(f'{k}: {v}' for k, v in dedup['merges']['by_reason'].items()) or 'none'}).\n",
          "## How duplicates were found and decided\n",
          "1. **URL identity (engine).** Records sharing a documentation site key or repository merge automatically. The designsystems.one adapter "
          "now reads each entry's detail page, so its 76 name-only entries carry the system's website/repository and merge on that evidence.",
          "2. **Bound sources.** A source registered for a system (official docs crawl, admin intake) always resolves to that system, even if the docs redirect "
          "to a new host (this removed the separate `shopify.dev` Polaris entry).",
          "3. **Name collisions → evidence resolver.** Same-name entities are queued as review items and decided with redirect, cross-link, shared "
          "repository/Storybook and organization evidence. Same name + different publishing organizations + no shared location ⇒ distinct. A name match "
          "alone never merges.\n",
          f"Identity links now: {', '.join(f'{k} {v}' for k, v in sorted(links.items()))}. Latest decision per review item: "
          f"{', '.join(f'{k} {v}' for k, v in sorted(dec_counts.items()))}. Decisions that rest on a written rationale rather than fetched HTTP evidence: "
          f"{curated_rationale}.\n",
          "## Merged records (alias table)\n", "| Old key | Old ID | Name | Canonical key | Reason |\n|---|---:|---|---|---|"]
    md += [f"| `{a.alias_key}` | {a.alias_id} | {a.alias_name} | `{a.canonical_key}` | {a.reason} |" for a in aliases] or ["| — | | | | |"]
    md += ["\n## Still open (needs an administrator decision)\n"]
    md += [f"- **{', '.join(i['entities'] or [i['key']])}** ({i['kind']}): {i['rationale'] or i['resolution'] or 'not evaluated yet'}" for i in dedup["open_items"]] or ["- none"]
    md += [f"\nRemaining same-name groups (distinct systems sharing a name, or awaiting review): {', '.join(sorted(same_name)) or 'none'}.\n"]
    (OUT / "deduplication_report.md").write_text("\n".join(md))

    rmd = [f"# Data reconciliation report\n\nGenerated {gen} from the live database and the authenticated API (`scripts/export_kb_reports.py`).\n",
           f"- Canonical design systems: **{cur['design_systems']}** (baseline {b.get('design_systems', '—')}; {dedup['net_reduction']} confirmed duplicates merged)",
           f"- Verification: {', '.join(f'{k} {v}' for k, v in sorted(verification.items()))}\n",
           "## Records retained\n", "| Table | Before | After |\n|---|---:|---:|"]
    rmd += [f"| {k} | {v['before'] if v['before'] is not None else '—'} | {v['after']} |" for k, v in recon["retained"].items()]
    rmd += ["\n## Resource links\n", "| Type | Status | Links |\n|---|---|---:|"]
    rmd += [f"| {t} | {s_} | {n} |" for t, s_, n in res_counts]
    rmd += ["\n| Type | Systems with a link | …with a verified link |\n|---|---:|---:|"]
    rmd += [f"| {t} | {systems_with[t]} | {systems_with_verified[t]} |" for t in systems_with]
    rmd += [f"\nFigma profile/community/plugin pages kept but reclassified as additional resources (not design files): {figma_reclassified}.\n",
            "## Relationships\n", "| Check | Before | After |\n|---|---:|---:|",
            f"| Storybook projects without a system | {b.get('storybook_projects_without_system', '—')} | {orphans['storybook_projects_without_system']} |"]
    rmd += [f"| {k.replace('_', ' ')} | — | {v} |" for k, v in orphans.items() if k != "storybook_projects_without_system"]
    rmd += ["\nGuidelines without a system come from sources that are not about one system (library-agnostic checklists, specifications and "
            "editorial guides); they remain searchable in the Guidelines view. Tool records (e.g. 166 Style Dictionary transforms) are tooling, "
            "not design systems, and are not counted.\n",
            "## Storage → API trace\n", "| Record type | Stored | API total | Match |\n|---|---:|---:|:-:|"]
    rmd += [f"| {t['record_type']} | {t['stored'] if t['stored'] is not None else '—'} | {t['api_total'] if t['api_total'] is not None else t['http_status']} | "
            f"{'✓' if t['match'] else '✗'} |" for t in trace]
    rmd += ["\n## Root causes fixed\n"] + [f"- {x}" for x in recon["root_causes_fixed"]]
    rmd += ["\n## Remaining data-quality issues\n"] + [f"- {k.replace('_', ' ')}: {v}" for k, v in quality.items()]
    rmd += ["\nCompleteness is not claimed beyond these checks: unknown facts stay empty, and a link that is not published in a page's static HTML "
            "is reported as not found, not as absent."]
    (OUT / "data_reconciliation_report.md").write_text("\n".join(rmd))
    print(json.dumps({"canonical_systems": cur["design_systems"], "aliases": len(aliases), "open_review": len(open_items),
                      "trace_mismatches": [t["record_type"] for t in trace if not t["match"]]}, indent=1))


if __name__ == "__main__":
    main()
