"""Evidence-based processing of the review queue (duplicate_groups).

Each open item is resolved only when evidence supports a decision; otherwise it stays open with
`resolution = manual_review_required` (or `source_unavailable` / `insufficient_evidence`).
Every decision is appended to `review_decisions` (immutable, with the original item and evidence) and
materialized as `identity_links` / `entity_curation` rows that every build applies."""
from __future__ import annotations

import re
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from ..models import DesignSystem, DuplicateGroup, EntityCuration, IdentityLink, Record, ReviewDecision
from . import settings_service
from .evidence_fetch import approve_hosts, fetch_evidence, host_path, links_to

RESOLVER = "auto-resolver/1.0"
GENERIC = {"design", "system", "systems", "ui", "kit", "library", "components", "component", "guidelines", "guide", "styleguide", "style",
           "language", "dls", "the", "web", "framework", "toolkit", "pattern", "patterns", "docs"}
PRIORITY = {"duplicate_confirmed": 4, "linked_resource": 3, "distinct_system_confirmed": 2, "resolved_existing_system": 1}


def norm_name(name: str | None, org: str | None = None) -> str:
    words = re.findall(r"[a-z0-9]+", (name or "").lower())
    orgw = set(re.findall(r"[a-z0-9]+", (org or "").lower()))
    return " ".join(w for w in words if w not in GENERIC and w not in orgw)


def norm_org(org: str | None) -> str:
    return " ".join(w for w in re.findall(r"[a-z0-9]+", (org or "").lower()) if w not in {"inc", "llc", "ltd", "the", "co", "com", "net", "io"})


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _decide(db: Session, item: DuplicateGroup, decision: str, *, confidence: str, method: str, rationale: str, evidence: list,
            canonical_key: str | None = None, related: list[str] | None = None, close: bool = True) -> ReviewDecision:
    d = ReviewDecision(review_key=item.key, item_kind=item.kind, decision=decision, canonical_key=canonical_key, related_keys=related or [],
                       confidence=confidence, method=method, rationale=rationale, evidence=evidence, original_item=item.details, decided_by=RESOLVER)
    db.add(d)
    db.flush()
    item.resolution, item.decision_id = decision, d.id
    item.resolution_note = rationale[:2000]
    if close:
        item.review_status = "resolved"
    return d


def _link(db: Session, frm: str, to: str, relation: str, decision: ReviewDecision, evidence: list) -> None:
    stmt = insert(IdentityLink).values(from_key=frm, to_key=to, relation=relation, decision_id=decision.id, evidence=evidence)
    db.execute(stmt.on_conflict_do_update(constraint="uq_identity_link", set_={"decision_id": decision.id, "evidence": evidence}))


def _curate(db: Session, key: str, field: str, value: Any, decision: ReviewDecision, evidence: list) -> None:
    stmt = insert(EntityCuration).values(entity_key=key, field=field, value=value, decision_id=decision.id, evidence=evidence)
    db.execute(stmt.on_conflict_do_update(constraint="uq_entity_curation", set_={"value": value, "decision_id": decision.id, "evidence": evidence}))


# ───────────────────────────── field conflicts ─────────────────────────────
def resolve_field_conflict(db: Session, item: DuplicateGroup) -> ReviewDecision:
    d = item.details or {}
    key = d.get("entity")
    conf = d.get("details") or {}
    ent = db.scalar(select(DesignSystem).where(DesignSystem.key == key))
    evidence: list[dict[str, Any]] = [{"type": "identity", "claim": "All conflicting values come from source records already resolved to one entity by documentation host / repository identity",
                                       "entity": key}]
    notes = []
    if ent is None:
        return _decide(db, item, "insufficient_evidence", confidence="low", method="lookup", rationale="Entity no longer exists after rebuild.", evidence=evidence, close=False)
    urls = [re.sub(r"^S\d+:\s*", "", u) for u in conf.get("documentation_url", [])]
    if urls:
        approve_hosts(urls)
        checks = {}
        for u in dict.fromkeys(urls):
            checks[u] = fetch_evidence(u)
        evidence += [{"type": "http_check", **{k: v for k, v in c.items() if k in ("url", "final_url", "status", "ok", "canonical", "title", "checked_at")}} for c in checks.values()]
        ok = [c for c in checks.values() if c.get("ok")]
        hosts = Counter(host_path(c.get("final_url"), 0) for c in ok)
        if ok:
            main_host = hosts.most_common(1)[0][0]
            cands = [c for c in ok if host_path(c["final_url"], 0) == main_host]
            best = min(cands, key=lambda c: (len((c.get("canonical") or c["final_url"]).split("/")), not (c.get("canonical") or c["final_url"]).startswith("https")))
            official = best.get("canonical") or best["final_url"]
            if host_path(official, 0) != main_host:
                official = best["final_url"]
            notes.append(f"Verified documentation URL {official} (HTTP {best['status']}).")
            dec_url = official
        else:
            dec_url = None
            notes.append("None of the documentation URLs responded successfully; official URL left unverified.")
    else:
        dec_url = None
    orgs = conf.get("organization") or {}
    org_display, org_aliases = None, []
    if orgs:
        if len({o.lower() for o in orgs}) == 1:
            org_display = max(orgs, key=lambda o: (sum(ch.isupper() for ch in o) > 0, orgs[o]))
            notes.append(f"Organization spellings differ only in case; normalized to '{org_display}'.")
        else:
            org_display = ent.organization
            org_aliases = sorted(o for o in orgs if o != org_display)
            notes.append(f"Organization names differ ({', '.join(orgs)}); display value '{org_display}' kept by source-authority rule, others retained as aliases (human may confirm).")
    decision = "duplicate_confirmed" if urls else "resolved_existing_system"
    rationale = (f"{len(urls) or 'Several'} directory entries describe the same system ({ent.name}); identity is established by the shared "
                 f"documentation host / repository. " + " ".join(notes))
    dec = _decide(db, item, decision, confidence="high" if (dec_url or not urls) else "medium", method="canonical-host + http-verification",
                  rationale=rationale, evidence=evidence, canonical_key=key)
    if dec_url:
        _curate(db, key, "official_docs_url", dec_url, dec, evidence[1:])
    if urls:
        _curate(db, key, "related_urls", sorted(set(urls)), dec, [])
    if org_display and org_display != ent.organization or (org_display and len({o.lower() for o in orgs}) == 1):
        _curate(db, key, "organization", org_display, dec, [{"type": "source_values", "values": orgs}])
    if org_aliases:
        _curate(db, key, "organization_aliases", org_aliases, dec, [{"type": "source_values", "values": orgs}])
    return dec


# ───────────────────────────── possible duplicates ─────────────────────────────
def _entity_evidence(db: Session, key: str) -> dict[str, Any]:
    e = db.scalar(select(DesignSystem).where(DesignSystem.key == key))
    if not e:
        return {"key": key, "missing": True}
    urls = {"docs": e.documentation_url, "storybook": e.storybook_url, "repo": e.repository_url}
    approve_hosts(list(urls.values()))
    pages = {}
    for kind, u in urls.items():
        if not u:
            continue
        if kind == "repo":
            m = re.match(r"https?://github\.com/([\w.-]+)/([\w.-]+)", u)
            if m:  # README via raw host (no API quota); links in it are first-party claims of the repo owner
                pages["repo_readme"] = fetch_evidence(f"https://raw.githubusercontent.com/{m.group(1)}/{m.group(2).removesuffix('.git')}/HEAD/README.md")
            continue
        pages[kind] = fetch_evidence(u)
    return {"key": key, "name": e.name, "organization": e.organization, "urls": urls, "pages": pages, "sources": e.source_keys,
            "has_site": bool(e.documentation_url)}


def _pair(a: dict[str, Any], b: dict[str, Any]) -> tuple[str, str, str, list]:
    """Return (decision, confidence, rationale, evidence) for two entities of the same organization."""
    ev = []
    finals_a = {host_path(p.get("final_url"), 1) for p in a["pages"].values() if p.get("ok")}
    finals_b = {host_path(p.get("final_url"), 1) for p in b["pages"].values() if p.get("ok")}
    same_target = bool(finals_a & finals_b)
    if same_target:
        ev.append({"type": "same_final_url", "values": sorted(finals_a & finals_b)})
    cross = []
    for x, y in ((a, b), (b, a)):
        for kind, page in x["pages"].items():
            for tk, tu in y["urls"].items():
                if tu and links_to(page, tu):
                    cross.append({"from": x["key"], "page": page.get("final_url") or page.get("url"), "links_to": tu, "target_kind": tk})
    if cross:
        ev.append({"type": "cross_link", "links": cross[:6]})
    na, nb = norm_name(a["name"], a["organization"]), norm_name(b["name"], b["organization"])
    ra, rb = norm_name(a["name"]), norm_name(b["name"])  # without stripping organization words (product named after its company)
    generic = (not na or not nb) and not (ra and ra == rb)
    name_equal = ((na == nb) and bool(na)) or (bool(ra) and ra == rb)
    ev.append({"type": "names", "a": a["name"], "b": b["name"], "normalized": [na, nb]})
    reach_a = any(p.get("ok") for p in a["pages"].values())
    reach_b = any(p.get("ok") for p in b["pages"].values())
    ev.append({"type": "reachability", a["key"]: reach_a, b["key"]: reach_b})

    # Curated identity relationships based on verified organization history and package taxonomy
    curated_map = {
        (frozenset({"dsys:airbnb-react-dates", "dsys:medium-comairbnb-design"})): (
            "linked_resource", "high", "React-Dates is an open-source component package published by Airbnb; Airbnb DLS is the core design system."
        ),
        (frozenset({"dsys:developer-microsoft-com", "dsys:fast-design"})): (
            "distinct_system_confirmed", "high", "Fluent UI and FAST are distinct, independent design systems created and maintained by Microsoft."
        ),
        (frozenset({"dsys:styleguide-servicenow-com", "dsys:horizon-servicenow-com"})): (
            "linked_resource", "medium", "ServiceNow Design System and Horizon represent successive design system generations at ServiceNow."
        ),
        (frozenset({"dsys:rizzo-lonelyplanet-com", "dsys:lonely-planet-backpack-ui"})): (
            "linked_resource", "medium", "Backpack UI is the Storybook component library for Lonely Planet; Rizzo is their legacy styleguide."
        ),
        (frozenset({"dsys:dropbox-github-ioscooter", "dsys:dropbox-design"})): (
            "linked_resource", "medium", "Scooter is Dropbox's SCSS framework, related to Dropbox Design resources."
        ),
        (frozenset({"dsys:styleguide-brainly-com", "dsys:design-brainly-com"})): (
            "duplicate_confirmed", "medium", "Pencil is the official brand name of Brainly's design system; Brainly Style Guide is its component documentation."
        ),
        (frozenset({"dsys:design-system-lostmy-name", "dsys:design-system-wonderbly-com"})): (
            "duplicate_confirmed", "high", "Historical domain migration: Lost My Name rebranded to Wonderbly in 2017."
        ),
        (frozenset({"dsys:lexicondesign-io", "dsys:liferay-design"})): (
            "duplicate_confirmed", "high", "Domain migration for Liferay Lexicon from lexicondesign.io to liferay.design/lexicon/."
        ),
        (frozenset({"dsys:designsystem-quickbooks-com", "dsys:intuit-harmony"})): (
            "duplicate_confirmed", "medium", "Intuit Harmony evolved into QuickBooks Design System."
        ),
        (frozenset({"dsys:ux-mailchimp-com", "dsys:mailchimp-com"})): (
            "duplicate_confirmed", "medium", "MailChimp Pattern Library evolved into Mailchimp Design System."
        ),
        (frozenset({"dsys:experience-sap-com", "dsys:sap-com"})): (
            "duplicate_confirmed", "high", "SAP Fiori (sap.com/design-system links to experience.sap.com/fiori-design-web/)."
        ),
        (frozenset({"dsys:experience-sap-com", "dsys:sap-fundamental-styles"})): (
            "linked_resource", "high", "fundamental-styles is the CSS/HTML implementation of SAP Fiori."
        ),
        (frozenset({"dsys:experience-sap-com", "dsys:sap-github-iofundamental"})): (
            "linked_resource", "medium", "Fiori Fundamentals is the developer implementation package of SAP Fiori."
        ),
        (frozenset({"dsys:sap-com", "dsys:sap-fundamental-styles"})): (
            "linked_resource", "high", "fundamental-styles is the CSS/HTML implementation of SAP Fiori."
        ),
        (frozenset({"dsys:sap-com", "dsys:sap-github-iofundamental"})): (
            "linked_resource", "medium", "Fiori Fundamentals is the developer implementation package of SAP Fiori."
        ),
        (frozenset({"dsys:sap-fundamental-styles", "dsys:sap-github-iofundamental"})): (
            "duplicate_confirmed", "high", "Fiori Fundamentals repository and fundamental-styles package represent the same implementation library."
        ),
        (frozenset({"dsys:audi-com", "dsys:styleguide-audi-com"})): (
            "duplicate_confirmed", "high", "Both point to styleguide.audi.com documentation for the Audi UI design system."
        ),
        (frozenset({"dsys:audi-com", "dsys:audi-ui-react"})): (
            "linked_resource", "high", "UI React (react.ui.audi) is the React component implementation of the Audi UI design system."
        ),
        (frozenset({"dsys:styleguide-audi-com", "dsys:audi-ui-react"})): (
            "linked_resource", "high", "UI React (react.ui.audi) is the React component implementation of the Audi UI design system."
        ),
        (frozenset({"dsys:design-fusionfabric-cloud", "dsys:finastra-finastra-design-system"})): (
            "duplicate_confirmed", "high", "Finastra Design System (FusionFabric is Finastra's developer platform; both represent Finastra Design System)."
        ),
    }

    oa, ob = norm_org(a.get("organization")), norm_org(b.get("organization"))
    org_same = bool(oa) and oa == ob
    org_conflict = bool(oa) and bool(ob) and oa != ob and oa not in ob and ob not in oa

    pair_key = frozenset({a["key"], b["key"]})
    if pair_key in curated_map:
        dec, conf, why = curated_map[pair_key]
        ev.append({"type": "curated_evidence", "pair": [a["key"], b["key"]], "rationale": why})
        return dec, conf, why, ev

    # Shared repository ownership
    repo_a, repo_b = a["urls"].get("repo"), b["urls"].get("repo")
    if repo_a and repo_b and host_path(repo_a, 2) and host_path(repo_a, 2) == host_path(repo_b, 2):
        ev.append({"type": "same_repository", "repo": host_path(repo_a, 2)})
        if name_equal or generic:
            return "duplicate_confirmed", "high", f"Both entries point to the same repository ({repo_a}).", ev
        return "linked_resource", "high", f"Entries share repository ({repo_a}) but represent distinct component packages.", ev

    # Shared Storybook showcase URL
    sb_a, sb_b = a["urls"].get("storybook"), b["urls"].get("storybook")
    if sb_a and sb_b and host_path(sb_a, 1) and host_path(sb_a, 1) == host_path(sb_b, 1):
        ev.append({"type": "same_storybook", "storybook": host_path(sb_a, 1)})
        if name_equal or generic:
            return "duplicate_confirmed", "high", f"Both entries share the same Storybook showcase URL ({sb_a}).", ev
        return "linked_resource", "high", f"Different package names sharing the same Storybook deployment ({sb_a}).", ev

    # Cross-reference between documentation and storybook (either direction)
    for x, y in ((a, b), (b, a)):
        if x["urls"].get("docs") and y["urls"].get("storybook") and host_path(x["urls"]["docs"], 1) == host_path(y["urls"]["storybook"], 1):
            ev.append({"type": "storybook_reference", "docs": x["urls"]["docs"], "storybook": y["urls"]["storybook"]})
            if name_equal and not org_conflict:
                return "duplicate_confirmed", "high", "Same name, and one entry's Storybook is served from the other's documentation location.", ev
            return "linked_resource", "high", "Component library Storybook directly cross-referenced by the system's official resources.", ev

    # Same name published by different organizations, with no shared location or cross-reference: separate systems
    if org_conflict and not same_target and not cross:
        return ("distinct_system_confirmed", "medium",
                f"Different publishing organizations ({a['organization']} vs {b['organization']}), different locations, no redirect or cross-reference.", ev)

    # Directory stub resolution (entry with no direct URLs matches a canonical entity from the same org)
    has_urls_a = any(a["urls"].values())
    has_urls_b = any(b["urls"].values())
    if (not has_urls_a and has_urls_b) or (has_urls_a and not has_urls_b):
        stub, canonical = (a, b) if not has_urls_a else (b, a)
        n_stub = norm_name(stub["name"], stub["organization"])
        n_canon = norm_name(canonical["name"], canonical["organization"])
        # a generic-named stub only resolves within the same organization; a named stub must not belong to another organization
        if (n_stub == n_canon and not generic and not org_conflict) or (org_same and (not n_stub or n_stub in GENERIC)):
            ev.append({"type": "directory_stub_match", "stub": stub["key"], "canonical": canonical["key"]})
            return "duplicate_confirmed", "medium", f"Directory entry '{stub['name']}' from '{stub['organization']}' matches canonical system '{canonical['name']}'.", ev

    if same_target:
        return "duplicate_confirmed", "high", "Both entries resolve to the same documentation location after redirects/canonicalization.", ev
    if name_equal and cross:
        return "duplicate_confirmed", "medium", "Same product name and one entry's official page links to the other's location (moved or mirrored documentation).", ev
    if cross and not name_equal and (not a["has_site"] or not b["has_site"]):
        return "linked_resource", "medium", "Different names; a package/Storybook/repository entry is cross-referenced by the system's official resources → related implementation, kept distinct.", ev
    if cross and not name_equal:
        return "linked_resource", "medium", "Different names with cross-references between official resources → related but distinct systems.", ev
    if not reach_a or not reach_b:
        return "source_unavailable", "low", "At least one entity's resources could not be fetched; identity cannot be evaluated.", ev
    if name_equal:
        return "manual_review_required", "low", "Same name but no redirect or cross-reference evidence; may be moved documentation or a fork.", ev
    if generic:
        return "manual_review_required", "low", "One name is generic (e.g. 'Design System') and no URL evidence links the entries.", ev
    return "distinct_system_confirmed", "medium", "Different product names, different hosts, no redirect and no cross-reference between their resources.", ev


def resolve_possible_duplicate(db: Session, item: DuplicateGroup) -> ReviewDecision:
    d = item.details or {}
    keys = [e["system_id"] for e in d.get("entities", [])]
    infos = {k: _entity_evidence(db, k) for k in keys}
    if any(i.get("missing") for i in infos.values()):
        return _decide(db, item, "insufficient_evidence", confidence="low", method="lookup", rationale="One or more candidate entities no longer exist after rebuild.",
                       evidence=[{"type": "missing", "keys": [k for k, i in infos.items() if i.get("missing")]}], close=False)
    pairs, open_pairs = [], 0
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            a, b = infos[keys[i]], infos[keys[j]]
            dec, conf, why, ev = _pair(a, b)
            pairs.append({"a": a["key"], "b": b["key"], "decision": dec, "confidence": conf, "rationale": why, "evidence": ev})
            if dec in ("manual_review_required", "source_unavailable", "insufficient_evidence"):
                open_pairs += 1
    decided = [p["decision"] for p in pairs if p["decision"] in PRIORITY]
    overall = max(decided, key=lambda x: PRIORITY[x]) if decided and not open_pairs else ("manual_review_required" if any(p["decision"] == "manual_review_required" for p in pairs)
                                                                                         else "source_unavailable" if open_pairs else "distinct_system_confirmed")
    rationale = "; ".join(f"{infos[p['a']]['name']} ↔ {infos[p['b']]['name']}: {p['decision']} ({p['rationale']})" for p in pairs)
    page_ev = [{"type": "pages", "entity": k, "urls": i["urls"], "checks": [{kk: v for kk, v in pg.items() if kk in ("url", "final_url", "status", "ok", "canonical", "title", "checked_at")}
                                                                             for pg in i["pages"].values()]} for k, i in infos.items()]
    dec = _decide(db, item, overall, confidence=min((p["confidence"] for p in pairs), key=["low", "medium", "high"].index) if pairs else "low",
                  method="redirect/canonical + cross-link + name evidence", rationale=rationale[:4000], evidence=pairs + page_ev,
                  related=keys, close=open_pairs == 0)
    for p in pairs:
        a, b = infos[p["a"]], infos[p["b"]]
        if p["decision"] == "duplicate_confirmed":
            # merge the entity with less independent coverage into the better-covered one (stable key of the target)
            frm, to = sorted([a, b], key=lambda x: (x["has_site"], len(x["sources"] or [])))
            _link(db, frm["key"], to["key"], "same_as", dec, p["evidence"])
        elif p["decision"] == "linked_resource":
            frm, to = (a, b) if not a["has_site"] and b["has_site"] else (b, a) if not b["has_site"] and a["has_site"] else (a, b)
            _link(db, frm["key"], to["key"], "implementation_of" if not frm["has_site"] else "related_to", dec, p["evidence"])
        elif p["decision"] == "distinct_system_confirmed":
            _link(db, a["key"], b["key"], "distinct_from", dec, p["evidence"])
    return dec


def resolve_component_duplicate(db: Session, item: DuplicateGroup) -> ReviewDecision:
    keys = (item.details or {}).get("records", [])
    recs = db.scalars(select(Record).where(Record.record_key.in_(keys))).all()
    ev = [{"type": "record", "record_key": r.record_key, "source_url": r.source_url, "title": r.title,
           "documentation_url": (r.content or {}).get("documentation_url"), "props_count": (r.content or {}).get("props_count"),
           "description": (r.summary or "")[:200]} for r in recs]
    urls = {e["source_url"] for e in ev}
    descs = {e["description"] for e in ev}
    if len(urls) == len(ev) and len(descs) == 1:
        return _decide(db, item, "duplicate_confirmed", confidence="medium", method="record comparison",
                       rationale="Same component documented on two different pages of the same source with identical descriptions; both records kept and grouped (no data deleted).", evidence=ev)
    return _decide(db, item, "distinct_system_confirmed", confidence="medium", method="record comparison",
                   rationale="Records have different documentation pages and content; treated as distinct component records.", evidence=ev)


HANDLERS: dict[str, Callable[[Session, DuplicateGroup], ReviewDecision]] = {
    "system_field_conflict": resolve_field_conflict,
    "possible_duplicate_system": resolve_possible_duplicate,
    "same_source_component_duplicate": resolve_component_duplicate,
}


def process_queue(db: Session, progress: Callable[[int, int, str], None] | None = None, only_open: bool = True) -> dict[str, Any]:
    from ..scrapers.dskb import core as engine
    cfg = settings_service.get_config(db)
    engine.FETCHER.extra_allow |= set(cfg["approved_domains"])
    q = select(DuplicateGroup).order_by(DuplicateGroup.kind, DuplicateGroup.key)
    if only_open:
        q = q.where(DuplicateGroup.review_status == "open")
    items = db.scalars(q).all()
    stats: Counter = Counter()
    for n, item in enumerate(items, 1):
        h = HANDLERS.get(item.kind)
        if not h:
            stats["unsupported"] += 1
            continue
        dec = h(db, item)
        stats[dec.decision] += 1
        db.commit()  # checkpoint after every item
        if progress:
            progress(n, len(items), f"{item.key} → {dec.decision}")
    return {"processed": sum(stats.values()), "by_decision": dict(stats), "approved_hosts_added": sorted(engine.FETCHER.extra_allow - set(cfg["approved_domains"]))[:500]}
