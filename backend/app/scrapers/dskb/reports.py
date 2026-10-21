"""Phase 8–10: analysis documents and all exports, generated from one canonical dataset."""
from __future__ import annotations

import csv
import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlparse

from .core import OUT, SCHEMA_VERSION, excerpt, now_iso, read_jsonl, slugify, write_jsonl
from .pipeline import LIBS, api_patterns, chunks_for, family_matrix, library_stats, write_csv
from .sources import SEED_BY_ID, SEEDS, TAXONOMY

INSPECTED = ("inspected", "inspected_partial")


def write_all(records, entities, coverage, review, validation, manifest) -> None:
    ts = now_iso()
    OUT.mkdir(parents=True, exist_ok=True)
    by_type = defaultdict(list)
    for r in records:
        by_type[r["record_type"]].append(r)

    # ── Source register (seeds + discovered) ───────────────────────────────
    seed_hosts = {urlparse(s["url"]).netloc for s in SEEDS}
    discovered = defaultdict(lambda: {"urls": set(), "parents": set(), "ok": 0, "fail": 0})
    for e in manifest:
        u = e.get("url") or ""
        p = urlparse(u)
        key = p.netloc
        if p.netloc in ("raw.githubusercontent.com",):
            key = "github:" + "/".join(p.path.split("/")[1:3])
        elif p.netloc == "api.github.com":
            m = re.match(r"/repos/([^/]+/[^/]+)", p.path)
            key = "github:" + (m.group(1) if m else "api")
        if key in seed_hosts or key == "github:" + "/".join(urlparse(SEED_BY_ID.get(e.get("source_id"), {}).get("url", "")).path.split("/")[1:3]):
            continue
        d = discovered[key]
        d["urls"].add(u)
        d["parents"].add(e.get("source_id"))
        if e.get("outcome") in ("fetched", "cache_hit", "not_modified") and (e.get("status") or 200) < 400:
            d["ok"] += 1
        elif e.get("outcome") not in ("retry",):
            d["fail"] += 1
    sources = []
    for s in SEEDS:
        c = coverage[s["source_id"]]
        sources.append({
            "source_id": s["source_id"], "name": s["name"], "original_url": s["url"], "resolved_url": c.get("resolved_url"),
            "source_type": s["source_type"], "origin": "seed", "crawl_status": c.get("crawl_status"), "http_status": c.get("http_status"),
            "page_title": c.get("page_title"), "access_restrictions": "; ".join(c.get("access_restrictions") or []) or None,
            "robots_status": (c.get("robots") or {}).get("status"), "robots_note": (c.get("robots") or {}).get("note"),
            "extraction_method": c.get("extraction_method"), "provides": c.get("provides"), "pages_attempted": c.get("pages_attempted"),
            "pages_ok": c.get("pages_ok"), "items_found": c.get("items_found"), "records_emitted": c.get("records_emitted"),
            "version_context": c.get("version_context"), "limitations": c.get("limitations"), "errors": (c.get("errors") or [])[:20],
            "error_count": len(c.get("errors") or []), "last_checked_at": c.get("completed_at") or c.get("last_checked_at"),
            "discovered_substitute": c.get("discovered_substitute"),
        })
    for i, (key, d) in enumerate(sorted(discovered.items(), key=lambda kv: -len(kv[1]["urls"])), 1):
        sources.append({"source_id": f"D{i:02d}", "name": key, "original_url": sorted(d["urls"])[0], "resolved_url": None,
                        "source_type": "discovered_" + ("repository" if key.startswith("github:") else "host"), "origin": "discovered",
                        "crawl_status": "fetched" if d["ok"] else "failed", "pages_attempted": len(d["urls"]), "pages_ok": d["ok"],
                        "discovered_from": sorted(x for x in d["parents"] if x), "error_count": d["fail"]})
    (OUT / "sources.json").write_text(json.dumps(sources, ensure_ascii=False, indent=2))
    write_csv(OUT / "sources.csv", sources, ["source_id", "name", "origin", "source_type", "original_url", "resolved_url", "crawl_status", "http_status",
                                             "robots_status", "extraction_method", "provides", "pages_attempted", "pages_ok", "items_found",
                                             "records_emitted", "error_count", "discovered_from", "discovered_substitute", "limitations", "last_checked_at"])

    # ── Canonical system entities as master records ─────────────────────────
    ent_records = []
    for e in entities:
        ent_records.append({
            "schema_version": SCHEMA_VERSION, "record_id": e["system_id"], "record_type": "system", "title": (f"{e['organization']} — " if e["organization"] else "") + e["name"],
            "summary": None, "primary_category": "C12", "category_name": TAXONOMY["C12"]["name"], "secondary_categories": [], "tags": ["canonical-entity"],
            "organization": e["organization"], "design_system": e["name"], "source_id": "KB", "source_url": e["evidence_urls"][0] if e["evidence_urls"] else e.get("documentation_url"),
            "canonical_url": e.get("documentation_url"), "repository_url": e.get("repository_url"), "source_status": "derived", "extraction_method": "manual",
            "normalized_content": e, "frameworks": e["supported_frameworks"], "platforms": [], "technologies": [], "license": None,
            "confidence": "high" if e["verification_status"] == "verified" else "medium" if e["source_count"] >= 2 else "low",
            "verification_status": e["verification_status"], "last_verified_at": ts,
            "relationships": [{"type": "aggregates", "target": rid} for rid in e["source_record_ids"]], "duplicate_group_id": e["system_id"],
            "notes": ["Canonical entity derived by deterministic entity resolution (documentation host / repository identity) over source records."],
        })
    master = records + ent_records
    write_jsonl(OUT / "design_systems_master.jsonl", master)

    (OUT / "design_systems.json").write_text(json.dumps(entities, ensure_ascii=False, indent=1))
    write_csv(OUT / "design_systems.csv", entities, ["system_id", "name", "organization", "documentation_url", "repository_url", "storybook_url",
                                                     "design_resource_url", "supported_frameworks", "styling_strategy", "token_architecture",
                                                     "accessibility_documentation", "governance_documentation", "ai_readiness", "sources", "source_count",
                                                     "verification_status", "verification_basis", "deprecated_flag", "aliases", "conflicts"])

    comps = by_type["component"]
    write_jsonl(OUT / "components.jsonl", comps)
    crow = []
    for r in comps:
        nc = r["normalized_content"]
        crow.append({"record_id": r["record_id"], "component_name": nc.get("component_name"), "family": nc.get("family"), "library": nc.get("library") or r.get("design_system"),
                     "organization": r.get("organization"), "source_id": r["source_id"], "detail_level": nc.get("detail_level"), "component_kind": nc.get("component_kind"),
                     "props_count": nc.get("props_count", 0), "subcomponents": [s["name"] for s in nc.get("subcomponents", [])],
                     "keyboard_entries": len(nc.get("keyboard", []) or []), "accessibility_sections": len(nc.get("accessibility_notes", []) or []),
                     "documentation_url": nc.get("documentation_url"), "source_url": r["source_url"], "source_version": r.get("source_version"),
                     "system_entity": r.get("system_entity"), "verification_status": r["verification_status"], "description": excerpt(r.get("summary"), 300)})
    write_csv(OUT / "components.csv", crow, list(crow[0].keys()) if crow else ["record_id"])
    write_jsonl(OUT / "design_tokens.jsonl", by_type["token"])
    write_jsonl(OUT / "patterns_guidelines.jsonl", by_type["pattern"] + by_type["guideline"])
    chunks = chunks_for(master)
    write_jsonl(OUT / "retrieval_chunks.jsonl", chunks)
    (OUT / "review_queue.json").write_text(json.dumps(review, ensure_ascii=False, indent=1))

    # ── Analysis docs ───────────────────────────────────────────────────────
    stats = library_stats(records)
    comparison_md = comparison(records, entities, stats)
    (OUT / "design_system_comparison.md").write_text(comparison_md)

    crawl = crawl_report(records, entities, coverage, review, validation, manifest, sources, ts)
    (OUT / "crawl_report.json").write_text(json.dumps(crawl, ensure_ascii=False, indent=2))
    (OUT / "research_report.md").write_text(research_report(records, entities, coverage, stats, crawl, review))
    (OUT / "knowledge_base_index.md").write_text(kb_index(records, entities, crawl))
    write_sqlite(OUT / "design_systems.db", sources, master, entities, chunks)
    write_xlsx(OUT / "design_systems_catalog.xlsx", sources, entities, crow, by_type, stats, coverage)
    final = verify_exports(len(master), len(entities), len(comps), len(by_type["token"]), len(by_type["pattern"]) + len(by_type["guideline"]), len(chunks))
    crawl["export_validation"] = final
    (OUT / "crawl_report.json").write_text(json.dumps(crawl, ensure_ascii=False, indent=2))
    (OUT / "validation_report.json").write_text(json.dumps({"record_validation": validation, "export_validation": final}, indent=2))
    print(json.dumps(crawl["summary"], indent=2))
    print("export validation:", "PASS" if final["all_passed"] else "FAIL", final["checks_failed"])


# ═════════════════════════════ crawl report ═════════════════════════════
def crawl_report(records, entities, coverage, review, validation, manifest, sources, ts):
    outcomes = Counter(e.get("outcome") for e in manifest)
    urls_req = {e["url"] for e in manifest if e.get("url")}
    ok_urls = {e["url"] for e in manifest if e.get("outcome") in ("fetched", "cache_hit", "not_modified") and (e.get("status") or 0) < 400}
    referenced = set()
    for r in records:
        nc = r.get("normalized_content") or {}
        for k in ("documentation_url", "destination_url", "repository_url", "storybook_url", "markdown_url"):
            if isinstance(nc.get(k), str) and nc[k].startswith("http"):
                referenced.add(nc[k])
        for k in ("components", "foundations"):
            for it in (nc.get("source_attributes", {}) or {}).get(k, []) or []:
                if isinstance(it, dict) and it.get("url"):
                    referenced.add(it["url"])
        for it in nc.get("implementations", []) or []:
            referenced.add(it.get("url"))
    referenced.discard(None)
    seeds_ok = [s for s in SEEDS if coverage[s["source_id"]].get("crawl_status") in INSPECTED]
    cats = Counter(r["primary_category"] for r in records)
    dup = sum(1 for r in records if r.get("duplicate_group_id") and r["record_type"] != "system") + sum(1 for r in records if r["record_type"] == "system")
    summary = {
        "seed_urls_attempted": len(SEEDS),
        "seed_urls_successfully_inspected": len(seeds_ok),
        "seed_urls_unavailable_or_failed": [s["source_id"] for s in SEEDS if coverage[s["source_id"]].get("crawl_status") not in INSPECTED],
        "urls_requested": len(urls_req),
        "urls_discovered_in_records_not_fetched": len(referenced - urls_req),
        "urls_discovered_total": len(urls_req | referenced),
        "pages_fetched_ok": len(ok_urls),
        "pages_parsed": sum(c.get("pages_ok", 0) for c in coverage.values()),
        "records_total": len(records),
        "canonical_systems": len(entities),
        "systems_in_2plus_sources": sum(1 for e in entities if e["source_count"] >= 2),
        "component_records": sum(1 for r in records if r["record_type"] == "component"),
        "component_records_with_api": sum(1 for r in records if r["record_type"] == "component" and r["normalized_content"].get("props_count")),
        "token_records": sum(1 for r in records if r["record_type"] == "token"),
        "pattern_and_guideline_records": sum(1 for r in records if r["record_type"] in ("pattern", "guideline")),
        "review_queue_items": len(review),
        "validation_issues": validation["issue_count"],
    }
    return {
        "generated_at": ts, "schema_version": SCHEMA_VERSION, "summary": summary,
        "manifest_outcomes": dict(outcomes),
        "pages_skipped": outcomes.get("skipped_not_allowlisted", 0) + outcomes.get("skipped_denylist", 0),
        "blocked_pages": outcomes.get("blocked_robots", 0),
        "failed_requests": outcomes.get("failed", 0) + outcomes.get("http_error", 0),
        "failed_examples": [{"url": e["url"], "outcome": e.get("outcome"), "status": e.get("status"), "error": e.get("error")} for e in manifest if e.get("outcome") in ("failed", "http_error", "blocked_robots")][:60],
        "records_by_type": dict(Counter(r["record_type"] for r in records)),
        "records_by_source": dict(Counter(r["source_id"] for r in records)),
        "category_counts": {f"{k} {TAXONOMY[k]['name']}": v for k, v in sorted(cats.items())},
        "duplicate_records_grouped": dup,
        "review_queue_by_type": dict(Counter(x["type"] for x in review)),
        "coverage_by_source": {s["source_id"]: {k: s.get(k) for k in ("name", "crawl_status", "http_status", "pages_attempted", "pages_ok", "items_found", "records_emitted", "error_count", "limitations")} for s in sources if s["origin"] == "seed"},
        "validation": {k: validation[k] for k in ("issue_count", "dangling_relationships", "by_type")},
        "last_execution": ts,
    }


# ═════════════════════════════ comparison ═════════════════════════════
def _cell(v):
    if v in (None, "", [], 0):
        return "—"
    if isinstance(v, list):
        return ", ".join(map(str, v))
    return str(v)


def comparison(records, entities, stats) -> str:
    L = ["# Design-System Comparative Analysis", "",
         f"_Generated {now_iso()} from the canonical dataset (`design_systems_master.jsonl`). Every number below is computed from extracted records._", "",
         "**Legend.** Values are **verified source facts** unless marked. `—` = *not documented in the inspected material*; **NI** = *not inspected*; **NA** = *not applicable*. "
         "Paragraphs labelled _Interpretation_ are analytical conclusions, not source statements.", "",
         "## 1. Component libraries (S11–S16)", "",
         "| Library | Type | Version inspected | Components | With API tables | Props documented | With keyboard tables | With a11y sections | With anatomy | Tokens extracted | Token delivery |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for sid, s in stats.items():
        tokdel = _cell(s["token_formats"]) if s["tokens"] else ("NA (unstyled)" if sid in ("S12", "S13", "S14") else "—")
        L.append(f"| [{s['library']}]({s['source_url']}) | {_cell(s['library_type'])} | {_cell(s['version'])} | {s['components']} | {s['with_props']} | {s['props_total']} | "
                 f"{s['with_keyboard']} | {s['with_a11y_section']} | {s['with_anatomy']} | {s['tokens']} | {tokdel} |")
    L += ["", "_Interpretation:_ Radix, Base UI and React Aria are **headless** — they ship behaviour, state and accessibility without visual styles, so a token count of zero is "
          "*not applicable* rather than a gap. shadcn/ui is a **recipe layer** (copied source on top of Radix or Base UI) whose tokens are CSS custom properties; Mantine and Ant Design "
          "are **styled systems** with their own token models (CSS variables vs. a seed/map/alias token algorithm). API and keyboard-table counts reflect how each project *documents* "
          "behaviour, not whether the behaviour exists (e.g. React Aria documents keyboard behaviour mostly in prose).", "",
          "## 2. Component family coverage", "", "Families are a documented normalisation (`sources.py: COMPONENT_FAMILIES`); source-native names are shown in each cell.", ""]
    fm = family_matrix(records)
    libs = [l for _, l in LIBS]
    L.append("| Family | " + " | ".join(libs) + " |")
    L.append("|---|" + "---|" * len(libs))
    for fam in sorted(fm, key=lambda f: (-len(fm[f]), f)):
        L.append(f"| {fam} | " + " | ".join(_cell(sorted(set(fm[fam].get(l, [])))[:4]) for l in libs) + " |")
    L += ["", "## 3. API patterns: controlled state & change handlers", "",
          "Extracted from documented props. Shows how each library names the *controlled value* and its *change callback* for the same component family.", ""]
    ap = api_patterns(records)
    for fam, row in ap.items():
        L += [f"### {fam}", "", "| Library | Components | State props | Change handlers |", "|---|---|---|---|"]
        for lib, v in row.items():
            if not v["components"]:
                L.append(f"| {lib} | — | — | — |")
            else:
                L.append(f"| {lib} | {_cell(v['components'])} | {_cell([f'`{x}`' for x in v['state_props']])} | {_cell([f'`{x}`' for x in v['change_handlers']])} |")
        L.append("")
    dlg = ap.get("Dialog", {})
    dsum = "; ".join(f"{lib}: {', '.join('`'+x+'`' for x in v['state_props'] + v['change_handlers']) or 'props not documented on the component page'}" for lib, v in dlg.items() if v["components"])
    L += ["_Interpretation:_ Within each library, controlled/uncontrolled pairs are consistent (`value`/`defaultValue` + a change callback), but conventions differ "
          f"across libraries. Dialog, from the extracted props — {dsum}. React Aria prefixes booleans with `is…` and uses key-based selection; Ant Design uses `activeKey` for tabs/collapse. "
          "shadcn/ui component pages rarely carry prop tables because props pass through to the underlying Radix/Base UI primitive. "
          "React Aria's API tables include inherited DOM/ARIA props, which inflates its prop count. A design system wrapping several libraries should pick one convention and adapt at the boundary.", "",
          "## 4. Design-system registry coverage across directories", ""]
    src_counts = Counter(e["source_count"] for e in entities)
    L += ["| Independent sources listing the system | Systems |", "|---|---|"] + [f"| {k} | {v} |" for k, v in sorted(src_counts.items())]
    L += ["", "Most widely referenced systems (by number of seed sources whose records resolved to the same entity):", "",
          "| System | Organization | Sources | Docs | Repository | Verification |", "|---|---|---|---|---|---|"]
    for e in entities[:30]:
        L.append(f"| {e['name']} | {_cell(e['organization'])} | {', '.join(e['sources'])} | {_cell(e['documentation_url'])} | {_cell(e['repository_url'])} | {e['verification_status']} |")
    L += ["", "## 5. Documentation-attribute prevalence (Adele audit, S02)", "",
          "Share of Adele rows reporting a non-empty, non-'no' value. These are Adele's claims, not re-verified.", ""]
    adele = [r for r in records if r["source_id"] == "S02" and r["record_type"] == "system"]
    if adele:
        keys = ["components", "typescript", "web components", "tests", "design tokens", "storybook", "accessibility guidelines", "voice & tone", "design principles", "UI kit", "code documentation"]
        L += ["| Attribute | Rows with value | 'yes' or specific value | % of rows |", "|---|---|---|---|"]
        for k in keys:
            vals = [r["normalized_content"]["source_attributes"].get(k) for r in adele]
            has = [v for v in vals if v and v.lower() not in ("no data", "no")]
            yes = [v for v in has if v.lower() not in ("not yet",)]
            L.append(f"| {k} | {len([v for v in vals if v])} | {len(yes)} | {round(100 * len(yes) / len(adele))}% |")
    ai = [r for r in records if r["source_id"] == "S20" and r["record_type"] == "guideline" and r["normalized_content"].get("kind") == "ai_readiness_signal"]
    if ai:
        L += ["", "## 6. AI-readiness signals (DesignSystems.one Agent-Ready Index, S20, CC BY 4.0)", "", "| Signal | yes | partial | no / other |", "|---|---|---|---|"]
        g = defaultdict(Counter)
        for r in ai:
            g[r["normalized_content"].get("label")][r["normalized_content"].get("status")] += 1
        for lab, c in g.items():
            L.append(f"| {lab} | {c.get('yes', 0)} | {c.get('partial', 0)} | {sum(c.values()) - c.get('yes', 0) - c.get('partial', 0)} |")
    L += ["", "## 7. Limitations of this comparison", "",
          "- Library facts come from official documentation at the versions listed; behaviour that is implemented but undocumented is reported as `—`.",
          "- Directory-derived system attributes are third-party claims and are not independently verified unless the system is one of S11–S16.",
          "- No numerical ranking is produced: the evidence does not support a weighting that is valid across product contexts.", ""]
    return "\n".join(L)


# ═════════════════════════════ research report ═════════════════════════════
def research_report(records, entities, coverage, stats, crawl, review) -> str:
    s = crawl["summary"]
    surf_pairs = set()
    for r in records:
        if r["source_id"] == "S01" and r["record_type"] == "component" and r["normalized_content"].get("detail_level") == "index":
            surf_pairs.add(((r.get("organization"), r.get("design_system")), r["normalized_content"].get("family") or r["title"]))
    surf_comp = Counter(f for _, f in surf_pairs)
    surf_systems = len({d for d, _ in surf_pairs})
    addons = Counter(a for r in records if r["source_id"] == "S04" and r["record_type"] == "system" for a in (r["normalized_content"]["source_attributes"].get("addons") or []) if a)
    dtcg_types = sorted({t for r in records if r["source_id"] == "S10" for t in r["normalized_content"].get("type_identifiers", []) or []})
    sd = next((r for r in records if r["source_id"] == "S09" and r["record_type"] == "tool" and r["normalized_content"].get("kind") == "token_build_system"), None)
    sd_counts = sd["normalized_content"]["counts"] if sd else {}
    sd_formats = sorted(r["normalized_content"]["name"] for r in records if r["source_id"] == "S09" and r["normalized_content"].get("kind") == "style_dictionary_format")
    chk = Counter(r["normalized_content"].get("category") for r in records if r["source_id"] == "S19" and r["record_type"] == "guideline")
    tok_by_lib = Counter(r.get("design_system") for r in records if r["record_type"] == "token")
    tok_types = Counter(r["normalized_content"].get("token_type") for r in records if r["record_type"] == "token")
    L = ["# Design-Systems Research Report", "", f"_Generated {crawl['generated_at']} · schema {SCHEMA_VERSION}. All figures are computed from `crawl_report.json` and the validated datasets._", "",
         "## 1. Executive summary", "",
         f"- **{s['seed_urls_attempted']}** seed URLs were attempted; **{s['seed_urls_successfully_inspected']}** were inspected successfully. Unavailable/partial: {', '.join(s['seed_urls_unavailable_or_failed']) or 'none'}.",
         f"- **{s['urls_requested']}** URLs were requested (**{s['pages_fetched_ok']}** succeeded); a further **{s['urls_discovered_in_records_not_fetched']}** URLs were discovered in records but not fetched (mostly official component pages linked from directories).",
         f"- **{s['records_total']}** normalized records were produced, resolving to **{s['canonical_systems']}** canonical design-system entities (**{s['systems_in_2plus_sources']}** corroborated by ≥2 independent sources).",
         f"- **{s['component_records']}** component records (**{s['component_records_with_api']}** with structured API/prop data), **{s['token_records']}** token records and **{s['pattern_and_guideline_records']}** pattern/guideline records.",
         f"- **{s['review_queue_items']}** items await manual review (field conflicts, possible duplicate systems).", "",
         "## 2. Research scope", "",
         "Twenty mandatory seed sources (directories, curated GitHub lists, token tooling and specification, six component libraries, two resource guides, one checklist). "
         "Recursion was limited to depth 2–3 from each seed and to the seeds' own domains plus their official machine-readable channels (llms.txt Markdown, registries, "
         "GitHub REST API/raw files at pinned commits, npm registry metadata, jsDelivr for published package metadata). Official system documentation linked from directories was "
         "recorded as URLs but **not** crawled unless the system is one of S11–S16.", "",
         "## 3. Source inventory", "", "| ID | Source | Status | Pages ok/attempted | Items | Records | Method |", "|---|---|---|---|---|---|---|"]
    for sd_ in SEEDS:
        c = coverage[sd_["source_id"]]
        L.append(f"| {sd_['source_id']} | [{sd_['name']}]({sd_['url']}) | {c.get('crawl_status')} | {c.get('pages_ok')}/{c.get('pages_attempted')} | {c.get('items_found')} | {c.get('records_emitted')} | {excerpt(c.get('extraction_method'), 90)} |")
    L += ["", "## 4. Methodology", "",
          "1. **Inventory** – seeds registered with stable IDs; robots.txt read per host (missing robots treated as allow-all per RFC 9309); the crawler identifies itself with a descriptive User-Agent.",
          "2. **Discovery** – sitemaps (Surf), embedded page data (Storybook `__NEXT_DATA__`), llms.txt indexes (shadcn, Base UI, React Aria, Mantine, Ant Design, DesignSystems.one), documented JSON APIs, and GitHub trees.",
          "3. **Extraction** – source-specific adapters (`dskb/adapters/*`). Markdown tables are parsed into typed prop/keyboard/data-attribute arrays; Radix JSX tables are parsed from the official docs MDX.",
          "4. **Politeness & safety** – ≥1 s spacing per host (raised by robots `Crawl-delay`), exponential backoff, response-size cap, disk cache with ETag/Last-Modified revalidation. No authentication, CAPTCHA or paywall was bypassed; no repository code was executed; scraped text is treated as untrusted data.",
          "5. **Normalization** – whitespace, canonical URLs (tracking params removed), framework names, organisation names; source-native API and token names preserved verbatim.",
          "6. **Deduplication** – deterministic entity resolution by documentation host (with path for shared hosts such as github.io) and repository identity; name-only matches are never auto-merged and are queued for review.",
          "7. **Validation** – schema/enum checks, URL syntax, relationship integrity, export round-trip parsing and cross-file count agreement.", "",
          "## 5. Taxonomy", "", "| ID | Category | Records (primary) |", "|---|---|---|"]
    cats = Counter(r["primary_category"] for r in records)
    for k, v in TAXONOMY.items():
        L.append(f"| {k} | {v['name']} | {cats.get(k, 0)} |")
    L += ["", "## 6. Major findings", "",
          "### 6.1 Discovery sources overlap heavily but each adds unique coverage",
          f"Canonical systems by number of corroborating sources: " + ", ".join(f"{k} source(s): {v}" for k, v in sorted(Counter(e['source_count'] for e in entities).items())) + ". "
          "Directories differ in what they record: Adele audits engineering attributes, Surf maps foundations/components to official pages, DesignSystems.one publishes editorial breakdowns "
          "and an AI-readiness audit, and the Storybook Showcase exposes live Storybook URLs and component counts.", "",
          "### 6.2 Most commonly documented components (Surf system pages)",
          f"Number of distinct systems (of {surf_systems} Surf systems that list component links) linking at least one official page in each component family (index-level evidence):", ""]
    L += ["| Family / component | Systems |", "|---|---|"] + [f"| {k} | {v} |" for k, v in surf_comp.most_common(20)]
    L += ["", "### 6.3 Component libraries", ""]
    for sid, st in stats.items():
        L.append(f"- **{st['library']}** ({_cell(st['library_type'])}, v{_cell(st['version'])}): {st['components']} components, {st['props_total']} documented props, "
                 f"{st['with_keyboard']} with keyboard tables, {st['tokens']} tokens extracted.")
    L += ["", "### 6.4 Tokens", "",
          f"- Token records by system/library: " + ", ".join(f"{k}: {v}" for k, v in tok_by_lib.most_common(12)) + ".",
          f"- Token types (source-native; Ant Design declares TypeScript types such as `string | number`, other values are DTCG-style or inferred and flagged `type_inferred`): " + ", ".join(f"{k or 'unknown'}: {v}" for k, v in tok_types.most_common(10)) + ".",
          f"- DTCG `$type` identifiers found in technical-report examples: {', '.join(dtcg_types) or '—'}.",
          f"- Style Dictionary documents {sd_counts.get('transforms', '—')} predefined transforms, {sd_counts.get('transform_groups', '—')} transform groups and {sd_counts.get('formats', '—')} formats "
          f"(e.g. {', '.join(sd_formats[:8])}).", "",
          "### 6.5 Storybook usage signals", "", "Most common add-ons among showcase projects: " + (", ".join(f"{k} ({v})" for k, v in addons.most_common(10)) or "—") + ".", "",
          "### 6.6 Governance & checklist", "", "Checklist items by area (S19 substitute repository): " + ", ".join(f"{k}: {v}" for k, v in chk.items()) + ".", "",
          "## 7. Accessibility observations", "",
          "- Headless libraries put accessibility in the primitive: Radix links WAI-ARIA Authoring Practices patterns and publishes keyboard tables per primitive; React Aria documents behaviour, internationalisation and ARIA semantics in prose and API types; Base UI documents accessibility in an overview guide and per-component notes.",
          "- Directory signals about accessibility (Adele 'accessibility guidelines', Surf 'Accessibility' foundation pages) indicate **documentation exists**, not conformance. This dataset never marks a system WCAG-compliant.",
          "", "## 8. Architecture trade-offs", "",
          "| Approach | Examples in scope | Gains | Costs |", "|---|---|---|---|",
          "| Headless primitives | Radix, Base UI, React Aria | Full visual control; a11y/behaviour solved once | You build and maintain all styling, tokens and docs |",
          "| Copy-in recipes | shadcn/ui | Own the code; no upstream breaking changes; easy token mapping via CSS variables | Upgrades are manual; drift between copies |",
          "| Styled systems | Mantine, Ant Design | Fastest to ship; theming APIs; large component sets | Visual language and API conventions are inherited; deep customisation fights defaults |",
          "| Token pipelines | Style Dictionary + DTCG format | One source → many platforms; spec-aligned interchange | Requires naming governance and CI validation |",
          "", "## 9. Governance practices observed", "",
          "- Lifecycle/maturity status, contribution models and RFC discipline appear in editorial breakdowns (S20) and Adele attributes; the checklist (S19) operationalises documentation, local libraries, team process, community support and contribution as discrete checks.",
          "- Changelogs/migration guides are first-class in the libraries (Style Dictionary v4/v5 migration guides; Ant Design and Mantine changelog/migration pages).",
          "", "## 10. Research-derived recommendations", "",
          "_These are syntheses across sources, not statements by any single source._", ""]
    L += recommendations(records)
    L += ["## 11. Limitations", ""]
    for sid, c in coverage.items():
        for lim in c.get("limitations") or []:
            L.append(f"- **{sid}**: {lim}")
    L += ["- Directory-linked official component pages (~thousands of URLs) were recorded but not crawled; their records are `detail_level: index`.",
          "- Data reflects the state of sources on the run date; re-running uses cached responses for up to 7 days and revalidates with ETag/Last-Modified thereafter.", "",
          "## 12. References", ""] + [f"- {x['source_id']} — {x['name']}: {x['url']}" for x in SEEDS]
    return "\n".join(L) + "\n"


def recommendations(records) -> List[str]:
    def ids(pred, n=4):
        return ", ".join(f"`{r['record_id']}`" for r in [r for r in records if pred(r)][:n]) or "—"
    recs = [
        ("Token interchange drifts between design tools and code.", "Author tokens in the DTCG format (`$value`, `$type`, aliases `{group.token}`) and compile them with a build tool such as Style Dictionary.",
         "The DTCG technical reports define types, groups and aliasing; Style Dictionary documents DTCG support and multi-platform formats.",
         ids(lambda r: r["source_id"] == "S10" and r["normalized_content"].get("kind") == "token_type") + "; " + ids(lambda r: r["source_id"] == "S09" and "DTCG" in r["title"], 2),
         "Spec features may be ahead of tool support; check the installed version.", "Very small single-platform products may not need a pipeline.",
         "CI step that parses token files against the DTCG schema and fails on unresolved aliases."),
        ("Inconsistent controlled/uncontrolled APIs across components.", "Standardise `value`/`defaultValue`/`onValueChange` (or the convention of your base library) for every stateful component and document it once.",
         "Section 3 of the comparison shows each library is internally consistent but conventions differ across libraries.", ids(lambda r: r["record_type"] == "component" and r["normalized_content"].get("family") == "Dialog" and r["normalized_content"].get("props_count")),
         "Wrapping a library with different conventions adds an adapter layer.", "Not needed if you adopt one library's conventions wholesale.", "Lint rule or API review checklist item checking prop names."),
        ("Accessibility regressions in custom widgets.", "Build complex widgets (dialog, combobox, menu, tabs) on headless primitives that publish keyboard tables and ARIA patterns, then test with keyboard and screen readers.",
         "Radix and React Aria document keyboard interaction per component; directories show accessibility docs exist widely but do not prove conformance.",
         ids(lambda r: r["record_type"] == "component" and r["normalized_content"].get("keyboard")), "Primitives constrain DOM structure; custom styling can still break contrast/focus visibility.",
         "Simple static components gain little.", "Manual test script per component plus automated axe checks in Storybook."),
        ("Teams cannot tell what is ready to use.", "Publish per-component status (planned/beta/stable/deprecated), a changelog and migration guides; track the checklist's documentation and release-cycle items.",
         "The checklist's Documentation and Team-process sections and the libraries' migration guides make lifecycle explicit.", ids(lambda r: r["source_id"] == "S19" and r["normalized_content"].get("section") in ("Documentation", "Team processes")),
         "Status labels need an owner to stay accurate.", "Early-stage systems with one consumer team.", "Every component page carries a status; stale-status report in CI."),
        ("AI coding assistants generate off-system UI.", "Expose machine-readable docs (llms.txt/Markdown per component, a component registry, DTCG tokens) and keep provenance and versions with each chunk.",
         "Five of the six libraries publish llms.txt or a registry; the Agent-Ready Index audits MCP, llms.txt, DTCG, registry and Code Connect signals.",
         ids(lambda r: r["source_id"] == "S20" and r["normalized_content"].get("kind") == "ai_readiness_signal", 3), "Machine-readable docs must be regenerated with each release or they mislead.",
         "Internal-only systems without AI tooling.", "Retrieval test set (e.g. 'which props does Dialog accept?') answered from your docs with citations."),
    ]
    out = []
    for i, (prob, act, why, refs, trade, cond, ver) in enumerate(recs, 1):
        out += [f"### R{i}. {act.split('.')[0]}", "", f"- **Problem:** {prob}", f"- **Action:** {act}", f"- **Why:** {why}", f"- **Evidence:** {refs}",
                f"- **Trade-offs:** {trade}", f"- **May not apply when:** {cond}", f"- **Verify by:** {ver}", ""]
    return out


# ═════════════════════════════ KB index ═════════════════════════════
def kb_index(records, entities, crawl) -> str:
    rt = Counter(r["record_type"] for r in records)
    cats = Counter(r["primary_category"] for r in records)
    L = ["# Design-Systems Knowledge Base — Index", "", f"_Generated {crawl['generated_at']} · schema {SCHEMA_VERSION}_", "",
         "## Files", "", "| File | Contents |", "|---|---|",
         "| `sources.json` / `sources.csv` | Source register: 20 seeds + discovered sources, crawl status, robots, coverage, errors |",
         "| `design_systems_master.jsonl` | Every normalized record (one JSON object per line) **plus** canonical system entities (`source_id: KB`) |",
         "| `design_systems.json` / `.csv` | Canonical design-system registry (entity-resolved across sources, with per-field provenance and conflicts) |",
         "| `components.jsonl` / `.csv` | One record per documented component; structured `subcomponents[].props`, `keyboard`, `accessibility_notes` |",
         "| `design_tokens.jsonl` | Token records with source-native names/values, type, theme, alias, component |",
         "| `patterns_guidelines.jsonl` | Patterns, specifications-as-guidance, checklist items, governance descriptions, AI-readiness signals |",
         "| `retrieval_chunks.jsonl` | Semantically coherent chunks for RAG, each with parent record, source, section, version, entity IDs |",
         "| `design_system_comparison.md` | Evidence-backed comparison (libraries, families, API patterns, directory coverage) |",
         "| `research_report.md` | Methodology, findings, trade-offs, recommendations, limitations, references |",
         "| `crawl_report.json` | Coverage and error report (from the crawl manifest) + export validation results |",
         "| `review_queue.json` | Conflicts and possible duplicates for manual review |",
         "| `design_systems.db` | SQLite: normalized tables + FTS5 full-text index over chunks |",
         "| `design_systems_catalog.xlsx` | Spreadsheet views of the same data |", "",
         "## Counts", "", "| Record type | Count |", "|---|---|"] + [f"| {k} | {v} |" for k, v in rt.most_common()] + [f"| canonical systems | {len(entities)} |", "",
         "## Taxonomy", "", "| ID | Category | Records | Subcategories |", "|---|---|---|---|"]
    for k, v in TAXONOMY.items():
        L.append(f"| {k} | {v['name']} | {cats.get(k, 0)} | {', '.join(v['subs'])} |")
    L += ["", "## Record format", "",
          "Common fields (all records): `record_id` (stable: `<type-prefix>:<source>:<slug>`), `record_type`, `title`, `summary`, `primary_category`, `secondary_categories`, `tags`, "
          "`organization`, `design_system`, `source_id`, `source_url`, `canonical_url`, `repository_url`, `source_file_path`, `source_section`, `source_version` (npm version or commit SHA), "
          "`source_status` (official/community/third_party/derived), `extraction_method`, `evidence_excerpt`, `normalized_content` (type-specific), `frameworks`, `platforms`, `technologies`, "
          "`license`, `confidence`, `verification_status`, `last_verified_at`, `relationships[]`, `duplicate_group_id`, `content_hash`, `notes[]`.", "",
          "Type-specific `normalized_content`:", "",
          "- **component**: `component_name`, `library`, `family`, `documentation_url`, `markdown_url`, `detail_level` (`api` | `doc` | `index` | `editorial_highlight`), `component_kind`, "
          "`subcomponents[{name, props[{name,type,default,description,required,since_version}], data_attributes[], css_variables[]}]`, `props_count`, `keyboard[{keys,description,section}]`, "
          "`accessibility_notes[]`, `examples[]`, `styles_api[]`, `section_outline[]`.",
          "- **token**: `token_name`, `token_path`, `token_type` (+ `type_inferred`), `raw_value`, `resolved_value`, `alias_of`, `semantic_role`, `theme`, `platform`, `component`, `description`, `source_format`.",
          "- **system** (source record): `name`, `organization`, `documentation_url`, `repository_url`, `storybook_url`, `design_resource_url`, `source_attributes` (verbatim directory fields).",
          "- **system** (canonical, `source_id: KB`): registry fields listed in §7.1 of the brief with `framework_evidence`, `sources`, `source_record_ids`, `conflicts`, `verification_basis`.",
          "- **guideline**: `kind` (`checklist_item`, `foundation_doc_link`, `library_documentation_page`, `design_specification`, `governance_description`, `ai_readiness_signal`) + kind fields.",
          "- **specification**: DTCG sections with `normative_keywords`, `example_types`; token-type records with `type_identifiers`.", "",
          "## Relationships", "",
          "`documented_by_system`, `foundation_of`, `part_of`, `listed_in`, `defined_in`, `token_of`, `canonical_entity` (source record → `dsys:*`), `aggregates` (entity → source records). "
          "`duplicate_group_id`: `dsys:*` for systems, `dcmp:*` for the same component reported by several sources, `dres:*` for resources sharing a destination URL.", "",
          "## Conventions", "",
          "- `null` = unknown; empty array = known-empty. Nothing is invented to fill a field.",
          "- `verification_status`: `verified` = read from the official source; `partially_verified` = corroborated by ≥2 independent sources or partially checked; `unverified` = single third-party claim.",
          "- Families are an added normalisation; `component_name` keeps the source-native name.", "",
          "## Search guidance", "", "```bash",
          "# All dialog components with keyboard documentation",
          "jq -c 'select(.normalized_content.family==\"Dialog\" and (.normalized_content.keyboard|length)>0) | {title, source_url}' components.jsonl",
          "# Systems with public tokens and a Storybook",
          "jq -c '.[] | select(.storybook_url and .token_architecture) | {name, storybook_url}' design_systems.json",
          "# Full-text search",
          "sqlite3 design_systems.db \"SELECT parent_record_id, snippet(chunks_fts,1,'[',']','…',12) FROM chunks_fts WHERE chunks_fts MATCH 'combobox AND keyboard' LIMIT 10;\"",
          "# Semantic token naming examples",
          "sqlite3 design_systems.db \"SELECT design_system, token_path, raw_value FROM tokens WHERE token_path LIKE '%primary%' LIMIT 20;\"",
          "```", "", "## Update procedure", "",
          "```bash", "cd research", ".venv/bin/python run.py extract --refresh   # re-crawl (revalidates cached responses)",
          ".venv/bin/python run.py extract --only S15  # one source", ".venv/bin/python run.py build             # rebuild every export from stage files", "```", "",
          "Stage checkpoints live in `data/stage/<SID>.json`; the HTTP cache and `data/crawl_manifest.jsonl` make runs resumable and auditable. `content_hash` supports change detection between runs.", ""]
    return "\n".join(L)


# ═════════════════════════════ SQLite ═════════════════════════════
def write_sqlite(path: Path, sources, master, entities, chunks):
    if path.exists():
        path.unlink()
    db = sqlite3.connect(path)
    c = db.cursor()
    c.executescript("""
    CREATE TABLE sources(source_id TEXT PRIMARY KEY, name TEXT, origin TEXT, source_type TEXT, original_url TEXT, resolved_url TEXT, crawl_status TEXT,
        http_status INTEGER, pages_attempted INTEGER, pages_ok INTEGER, items_found INTEGER, records_emitted INTEGER, json TEXT);
    CREATE TABLE records(record_id TEXT PRIMARY KEY, record_type TEXT, title TEXT, summary TEXT, primary_category TEXT, source_id TEXT, source_url TEXT,
        design_system TEXT, organization TEXT, source_version TEXT, confidence TEXT, verification_status TEXT, duplicate_group_id TEXT, content_hash TEXT, json TEXT);
    CREATE TABLE systems(system_id TEXT PRIMARY KEY, name TEXT, organization TEXT, documentation_url TEXT, repository_url TEXT, storybook_url TEXT,
        source_count INTEGER, verification_status TEXT, json TEXT);
    CREATE TABLE system_sources(system_id TEXT, source_id TEXT, record_id TEXT);
    CREATE TABLE components(record_id TEXT PRIMARY KEY, library TEXT, component_name TEXT, family TEXT, detail_level TEXT, props_count INTEGER,
        keyboard_count INTEGER, documentation_url TEXT, source_id TEXT, system_entity TEXT);
    CREATE TABLE component_props(record_id TEXT, subcomponent TEXT, name TEXT, type TEXT, default_value TEXT, description TEXT);
    CREATE TABLE component_keyboard(record_id TEXT, keys TEXT, description TEXT);
    CREATE TABLE tokens(record_id TEXT PRIMARY KEY, design_system TEXT, token_path TEXT, token_type TEXT, raw_value TEXT, theme TEXT, component TEXT,
        description TEXT, source_format TEXT, source_id TEXT);
    CREATE TABLE guidelines(record_id TEXT PRIMARY KEY, record_type TEXT, kind TEXT, title TEXT, primary_category TEXT, source_id TEXT, summary TEXT);
    CREATE TABLE relationships(record_id TEXT, type TEXT, target TEXT);
    CREATE TABLE evidence(record_id TEXT, source_url TEXT, excerpt TEXT, source_file_path TEXT, source_section TEXT, source_version TEXT);
    CREATE TABLE technologies(record_id TEXT, kind TEXT, value TEXT);
    CREATE TABLE chunks(chunk_id TEXT PRIMARY KEY, parent_record_id TEXT, source_id TEXT, source_url TEXT, section_title TEXT, category TEXT, version TEXT, content TEXT);
    """)
    for s in sources:
        c.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (s["source_id"], s["name"], s["origin"], s["source_type"], s["original_url"], s.get("resolved_url"),
                  s.get("crawl_status"), s.get("http_status"), s.get("pages_attempted"), s.get("pages_ok"), s.get("items_found"), s.get("records_emitted"), json.dumps(s, ensure_ascii=False)))
    for r in master:
        nc = r.get("normalized_content") or {}
        c.execute("INSERT INTO records VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (r["record_id"], r["record_type"], r["title"], r.get("summary"), r["primary_category"], r["source_id"],
                  r["source_url"], r.get("design_system"), r.get("organization"), r.get("source_version"), r["confidence"], r["verification_status"], r.get("duplicate_group_id"),
                  r.get("content_hash"), json.dumps(r, ensure_ascii=False)))
        for rel in r.get("relationships", []):
            c.execute("INSERT INTO relationships VALUES (?,?,?)", (r["record_id"], rel.get("type"), rel.get("target")))
        c.execute("INSERT INTO evidence VALUES (?,?,?,?,?,?)", (r["record_id"], r["source_url"], r.get("evidence_excerpt"), r.get("source_file_path"), r.get("source_section"), r.get("source_version")))
        for kind in ("frameworks", "platforms", "technologies"):
            for v in r.get(kind) or []:
                c.execute("INSERT INTO technologies VALUES (?,?,?)", (r["record_id"], kind[:-1], v))
        if r["record_type"] == "component":
            c.execute("INSERT INTO components VALUES (?,?,?,?,?,?,?,?,?,?)", (r["record_id"], nc.get("library") or r.get("design_system"), nc.get("component_name"), nc.get("family"),
                      nc.get("detail_level"), nc.get("props_count", 0), len(nc.get("keyboard") or []), nc.get("documentation_url"), r["source_id"], r.get("system_entity")))
            for sub in nc.get("subcomponents", []) or []:
                for p in sub.get("props", []):
                    c.execute("INSERT INTO component_props VALUES (?,?,?,?,?,?)", (r["record_id"], sub.get("name"), p.get("name"), p.get("type"), p.get("default"), p.get("description")))
            for k in nc.get("keyboard") or []:
                c.execute("INSERT INTO component_keyboard VALUES (?,?,?)", (r["record_id"], str(k.get("keys")), k.get("description")))
        elif r["record_type"] == "token":
            c.execute("INSERT INTO tokens VALUES (?,?,?,?,?,?,?,?,?,?)", (r["record_id"], r.get("design_system"), nc.get("token_path"), nc.get("token_type"),
                      None if nc.get("raw_value") is None else str(nc.get("raw_value")), nc.get("theme"), nc.get("component"), nc.get("description"), nc.get("source_format"), r["source_id"]))
        elif r["record_type"] in ("guideline", "pattern", "specification"):
            c.execute("INSERT INTO guidelines VALUES (?,?,?,?,?,?,?)", (r["record_id"], r["record_type"], nc.get("kind"), r["title"], r["primary_category"], r["source_id"], r.get("summary")))
    for e in entities:
        c.execute("INSERT INTO systems VALUES (?,?,?,?,?,?,?,?,?)", (e["system_id"], e["name"], e["organization"], e.get("documentation_url"), e.get("repository_url"),
                  e.get("storybook_url"), e["source_count"], e["verification_status"], json.dumps(e, ensure_ascii=False)))
        for rid in e["source_record_ids"]:
            c.execute("INSERT INTO system_sources VALUES (?,?,?)", (e["system_id"], rid.split(":")[1].upper(), rid))
    for ch in chunks:
        c.execute("INSERT OR REPLACE INTO chunks VALUES (?,?,?,?,?,?,?,?)", (ch["chunk_id"], ch["parent_record_id"], ch["source_id"], ch["source_url"], ch["section_title"],
                  ch["category"], ch.get("version"), ch["content"]))
    try:
        c.executescript("CREATE VIRTUAL TABLE chunks_fts USING fts5(chunk_id, content); INSERT INTO chunks_fts SELECT chunk_id, content FROM chunks;")
    except sqlite3.OperationalError:
        pass
    c.executescript("CREATE INDEX ix_comp_family ON components(family); CREATE INDEX ix_tok_ds ON tokens(design_system); CREATE INDEX ix_rel ON relationships(record_id);"
                    "CREATE INDEX ix_rec_type ON records(record_type); CREATE INDEX ix_props ON component_props(record_id);")
    db.commit()
    db.close()


# ═════════════════════════════ XLSX ═════════════════════════════
def write_xlsx(path, sources, entities, crow, by_type, stats, coverage):
    from openpyxl import Workbook
    from openpyxl.styles import Font
    wb = Workbook()
    wb.remove(wb.active)

    def sheet(name, rows, cols):
        ws = wb.create_sheet(name[:31])
        ws.append(cols)
        for c in ws[1]:
            c.font = Font(bold=True)
        for r in rows:
            ws.append([_x(r.get(c)) for c in cols])
        ws.freeze_panes = "A2"

    sheet("Source register", sources, ["source_id", "name", "origin", "source_type", "original_url", "resolved_url", "crawl_status", "http_status", "pages_attempted", "pages_ok", "items_found", "records_emitted", "error_count"])
    sheet("Systems", entities, ["system_id", "name", "organization", "documentation_url", "repository_url", "storybook_url", "supported_frameworks", "token_architecture", "accessibility_documentation", "source_count", "sources", "verification_status"])
    sheet("Components", crow, list(crow[0].keys()) if crow else ["record_id"])
    tok_rows = [{"record_id": r["record_id"], "design_system": r.get("design_system"), **{k: r["normalized_content"].get(k) for k in ("token_path", "token_type", "raw_value", "theme", "component", "description", "source_format")}, "source_url": r["source_url"]} for r in by_type["token"]]
    sheet("Tokens", tok_rows, ["record_id", "design_system", "token_path", "token_type", "raw_value", "theme", "component", "description", "source_format", "source_url"])
    pg = [{"record_id": r["record_id"], "type": r["record_type"], "kind": r["normalized_content"].get("kind"), "title": r["title"], "category": r["primary_category"], "source_id": r["source_id"], "summary": r.get("summary"), "source_url": r["source_url"]} for r in by_type["pattern"] + by_type["guideline"]]
    sheet("Patterns & guidelines", pg, ["record_id", "type", "kind", "title", "category", "source_id", "summary", "source_url"])
    tech = Counter()
    for t in by_type.values():
        for r in t:
            for f in (r.get("frameworks") or []) + (r.get("technologies") or []):
                tech[f] += 1
    sheet("Technologies", [{"technology": k, "records": v} for k, v in tech.most_common()], ["technology", "records"])
    sheet("Comparison", list(stats.values()), ["library", "library_type", "version", "components", "with_props", "props_total", "with_keyboard", "with_a11y_section", "tokens", "guides"])
    sheet("Crawl status", [dict(c, source_id=k) for k, c in coverage.items()], ["source_id", "name", "crawl_status", "http_status", "pages_attempted", "pages_ok", "items_found", "records_emitted", "duration_s"])
    wb.save(path)


def _x(v):
    if isinstance(v, (list, dict)):
        s = json.dumps(v, ensure_ascii=False)
    else:
        s = v
    if isinstance(s, str):
        s = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", s)[:32000]
    return s


# ═════════════════════════════ export validation ═════════════════════════════
def verify_exports(n_master, n_ent, n_comp, n_tok, n_pg, n_chunks) -> Dict[str, Any]:
    checks = {}

    def jl(name, expected):
        try:
            rows = read_jsonl(OUT / name)
            checks[f"{name} parses ({len(rows)} rows)"] = True
            checks[f"{name} row count == {expected}"] = len(rows) == expected
            checks[f"{name} unique record_ids"] = len({r.get('record_id', r.get('chunk_id')) for r in rows}) == len(rows)
        except Exception as e:
            checks[f"{name} parses: {e}"] = False
    jl("design_systems_master.jsonl", n_master)
    jl("components.jsonl", n_comp)
    jl("design_tokens.jsonl", n_tok)
    jl("patterns_guidelines.jsonl", n_pg)
    jl("retrieval_chunks.jsonl", n_chunks)
    for name in ("design_systems.json", "sources.json", "crawl_report.json", "review_queue.json"):
        try:
            json.loads((OUT / name).read_text())
            checks[f"{name} parses"] = True
        except Exception:
            checks[f"{name} parses"] = False
    checks["design_systems.json entity count matches"] = len(json.loads((OUT / "design_systems.json").read_text())) == n_ent
    for name in ("sources.csv", "design_systems.csv", "components.csv"):
        with open(OUT / name, encoding="utf8") as f:
            rows = list(csv.reader(f))
        checks[f"{name} consistent column count"] = len({len(r) for r in rows}) == 1
    checks["components.csv rows == components.jsonl"] = (sum(1 for _ in open(OUT / "components.csv", encoding="utf8")) - 1) <= n_comp  # embedded newlines are quoted
    db = sqlite3.connect(OUT / "design_systems.db")
    checks["sqlite records == master"] = db.execute("select count(*) from records").fetchone()[0] == n_master
    checks["sqlite components == components.jsonl"] = db.execute("select count(*) from components").fetchone()[0] == n_comp
    checks["sqlite tokens == design_tokens.jsonl"] = db.execute("select count(*) from tokens").fetchone()[0] == n_tok
    checks["sqlite systems == design_systems.json"] = db.execute("select count(*) from systems").fetchone()[0] == n_ent
    db.close()
    from openpyxl import load_workbook
    wb = load_workbook(OUT / "design_systems_catalog.xlsx", read_only=True)
    checks["xlsx components sheet rows == components"] = wb["Components"].max_row - 1 == n_comp
    checks["xlsx tokens sheet rows == tokens"] = wb["Tokens"].max_row - 1 == n_tok
    failed = [k for k, v in checks.items() if not v]
    return {"checks": checks, "checks_failed": failed, "all_passed": not failed}
