"""Phases 4–9: normalize → categorize → deduplicate → validate → analyze → export.
Every export is generated from the same in-memory canonical dataset."""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from .core import MANIFEST, OUT, SCHEMA_VERSION, STAGE, canonical_url, excerpt, now_iso, slugify, write_jsonl
from .sources import ALIAS_TO_FAMILY, LIB_FAMILY_OVERRIDES, SEED_BY_ID, SEEDS, TAXONOMY

FRAMEWORK_NAMES = {
    "react": "React", "reactjs": "React", "react.js": "React", "react native": "React Native", "vue": "Vue", "vue.js": "Vue",
    "vuejs": "Vue", "angular": "Angular", "angularjs": "AngularJS", "svelte": "Svelte", "web components": "Web Components",
    "webcomponents": "Web Components", "lit": "Lit", "stencil": "Stencil", "ember": "Ember", "preact": "Preact",
    "html/css": "HTML/CSS", "css": "CSS", "jquery": "jQuery", "polymer": "Polymer", "solid": "Solid", "flutter": "Flutter",
}
GENERIC_HOSTS = ("github.io", "github.com", "gitlab.com", "gitlab.io", "medium.com", "netlify.app", "vercel.app", "zeroheight.com",
                 "figma.com", "notion.site", "bitbucket.org", "storybook.js.org", "herokuapp.com", "supernova-docs.io", "frontify.com")
KEYWORD_CATS = [
    (r"\btoken", "C03"), (r"accessib|wcag|aria|keyboard|screen reader|a11y", "C07"), (r"theme|theming|dark mode|brand", "C10"),
    (r"govern|contribut|release|deprecat|changelog|version|documentation|roadmap|support", "C08"),
    (r"storybook|typescript|test|ci\b|build|figma|plugin|tailwind|css|ssr|bundle", "C09"),
    (r"color|colour|typograph|spacing|grid|layout|icon|motion|elevation|shadow", "C02"),
    (r"\bios\b|android|react native|cross-platform|flutter|native", "C11"), (r"llm|mcp|\bai\b|agent|machine-readable", "C13"),
    (r"form|search|filter|onboarding|empty state|error|wizard|checkout|navigation", "C06"),
]


def _h(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


# ───────────────────────────── load ─────────────────────────────
def load_stage() -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    records, coverage = [], {}
    for seed in SEEDS:
        p = STAGE / f"{seed['source_id']}.json"
        if not p.exists():
            from .adapters.common import new_coverage
            c = new_coverage(seed)
            c["crawl_status"] = "not_run"
            coverage[seed["source_id"]] = c
            continue
        d = json.loads(p.read_text(encoding="utf8"))
        records.extend(d["records"])
        coverage[seed["source_id"]] = d["coverage"]
    return records, coverage


# ───────────────────────────── normalize ─────────────────────────────
def norm_framework(f: str) -> Optional[str]:
    k = f.strip().lower()
    if not k or k in ("no", "no data", "none", "n/a", "-", "yes", "not yet"):
        return None
    return FRAMEWORK_NAMES.get(k, f.strip())


def norm_org(o: Optional[str]) -> Optional[str]:
    if not o:
        return None
    o = re.sub(r"\s+", " ", o).strip()
    return o


def normalize(records: List[Dict[str, Any]]) -> None:
    for r in records:
        for k in ("title", "summary", "evidence_excerpt"):
            if isinstance(r.get(k), str):
                r[k] = re.sub(r"\s+", " ", r[k]).strip() or None
        r["canonical_url"] = canonical_url(r.get("source_url"))
        r["organization"] = norm_org(r.get("organization"))
        r["frameworks"] = sorted({x for x in (norm_framework(f) for f in r.get("frameworks", [])) if x})
        nc = r.get("normalized_content") or {}
        for key in ("documentation_url", "destination_url", "repository_url"):
            if nc.get(key):
                nc[key.replace("_url", "_canonical")] = canonical_url(nc[key])
        r["content_hash"] = _h({"t": r.get("title"), "s": r.get("summary"), "n": nc})


# ───────────────────────────── categorize ─────────────────────────────
def categorize(records: List[Dict[str, Any]]) -> None:
    for r in records:
        if r["primary_category"] not in TAXONOMY:
            r["notes"].append(f"Invalid category {r['primary_category']} replaced with C12")
            r["primary_category"] = "C12"
        text = " ".join(filter(None, [r.get("title"), r.get("summary"), r.get("source_section") or ""])).lower()
        sec = set(r.get("secondary_categories") or [])
        for pat, cat in KEYWORD_CATS:
            if cat != r["primary_category"] and re.search(pat, text):
                sec.add(cat)
        if r["record_type"] == "component":
            sec.add("C04")
            cname = r["normalized_content"].get("component_name") or r["title"]
            ov = LIB_FAMILY_OVERRIDES.get(r.get("design_system") or "", {})
            fam = ov[cname] if cname in ov else family_for(cname)
            r["normalized_content"]["family"] = fam
            if fam:
                r["tags"] = sorted(set(r.get("tags", []) + [f"family:{slugify(fam)}"]))
        r["secondary_categories"] = sorted(sec - {r["primary_category"]})
        r["category_name"] = TAXONOMY[r["primary_category"]]["name"]


def family_for(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    n = re.sub(r"([a-z])([A-Z])", r"\1 \2", name).lower().replace("-", " ").strip()
    return ALIAS_TO_FAMILY.get(n) or ALIAS_TO_FAMILY.get(n.replace(" ", "")) or ALIAS_TO_FAMILY.get(n.rstrip("s"))


# ───────────────────────────── deduplicate ─────────────────────────────
def site_key(url: Optional[str]) -> Optional[str]:
    if not url or not url.startswith("http"):
        return None
    p = urlparse(canonical_url(url))
    host = p.netloc.lower()
    host = host[4:] if host.startswith("www.") else host
    segs = [s for s in p.path.split("/") if s]
    if any(host == g or host.endswith("." + g) for g in GENERIC_HOSTS):
        if host in ("github.com", "gitlab.com", "bitbucket.org", "medium.com", "figma.com"):
            return f"{host}/{'/'.join(segs[:2]).lower()}" if segs else host
        return f"{host}/{segs[0].lower()}" if segs else host
    return host


def repo_key(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    m = re.match(r"https?://(?:www\.)?(github\.com|gitlab\.com|bitbucket\.org)/([\w.-]+)/([\w.-]+)", url)
    return f"{m.group(1)}/{m.group(2).lower()}/{m.group(3).lower().removesuffix('.git') if hasattr(str,'removesuffix') else m.group(3).lower()}" if m else None


LIB_SITES = {"S11": "ui.shadcn.com", "S12": "radix-ui.com", "S13": "base-ui.com", "S14": "react-aria.adobe.com", "S15": "mantine.dev", "S16": "ant.design"}
SITE_ALIASES = {"react-spectrum.adobe.com/react-aria": "react-aria.adobe.com", "radix-ui.com/primitives": "radix-ui.com", "material.io": "m3.material.io",
                "carbondesignsystem.com": "carbondesignsystem.com"}


class UnionFind:
    def __init__(self):
        self.p: Dict[str, str] = {}

    def find(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[max(ra, rb)] = min(ra, rb)


def dedupe_systems(records: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    sys_recs = [r for r in records if r["record_type"] == "system"]
    # Official library entities from S11–S16 participate as systems too
    lib_tools = [r for r in records if r["record_type"] == "tool" and r["normalized_content"].get("kind") == "component_library"]
    uf = UnionFind()
    keys: Dict[str, Dict[str, Optional[str]]] = {}
    for r in sys_recs + lib_tools:
        nc = r["normalized_content"]
        doc = nc.get("documentation_url") or (SEED_BY_ID[r["source_id"]]["url"] if r in lib_tools else None)
        sk = site_key(doc)
        sk = SITE_ALIASES.get(sk, sk)
        if r in lib_tools:
            sk = LIB_SITES[r["source_id"]]
        rk = repo_key(r.get("repository_url") or nc.get("repository_url"))
        keys[r["record_id"]] = {"site": sk, "repo": rk}
        uf.find(r["record_id"])
        if sk:
            uf.union(r["record_id"], "site:" + sk)
        if rk and not rk.endswith(("/design-system", "/designsystem")):  # generic repo names alone are weak identifiers
            uf.union(r["record_id"], "repo:" + rk)
        if not sk and not rk:
            nk = f"name:{slugify((r.get('organization') or '') + ' ' + (nc.get('name') or r['title']))}"
            uf.union(r["record_id"], nk)
    groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in sys_recs + lib_tools:
        groups[uf.find(r["record_id"])].append(r)

    entities, review, used_ids = [], [], set()
    for root, members in groups.items():
        site = next((keys[m["record_id"]]["site"] for m in members if keys[m["record_id"]]["site"]), None)
        name_votes = Counter((m["normalized_content"].get("name") or m.get("design_system") or m["title"]).strip() for m in members)
        org_votes = Counter(m.get("organization") for m in members if m.get("organization"))
        # Prefer the most authoritative / most recently maintained source for the display name
        prio = ["official", "S20", "S01", "S04", "S16", "S02", "S06", "S03", "S07", "S08"]
        def _src_rank(m):
            return prio.index("official") if m["record_type"] == "tool" else (prio.index(m["source_id"]) if m["source_id"] in prio else 99)
        ranked = sorted(members, key=_src_rank)
        top = ranked[0]
        name = (top["normalized_content"].get("name") or top.get("design_system") or top["title"]).strip() if top["record_type"] != "tool" else top["title"]
        org = next((m.get("organization") for m in ranked if m.get("organization")), None)
        eid = base_eid = f"dsys:{slugify(site or (org or '') + '-' + name)}"
        n = 2
        while eid in used_ids:
            eid = f"{base_eid}-{n}"
            n += 1
        used_ids.add(eid)
        def pick(field):
            vals = [(m["source_id"], m["normalized_content"].get(field) or (m.get("repository_url") if field == "repository_url" else None)) for m in members]
            vals = [(s, v) for s, v in vals if v]
            return vals
        docs = pick("documentation_url")
        repos_ = pick("repository_url")
        sb = pick("storybook_url")
        fig = pick("design_resource_url")
        frameworks = defaultdict(set)
        for m in members:
            for f in m.get("frameworks", []):
                frameworks[f].add(m["source_id"])
        attrs = {m["source_id"]: m["normalized_content"].get("source_attributes") for m in members if m["normalized_content"].get("source_attributes")}
        adele = attrs.get("S02") or {}
        surf = attrs.get("S01") or {}
        sbk = attrs.get("S04") or {}
        one = attrs.get("S20") or {}
        official = [m for m in members if m["record_type"] == "tool"]
        ent = {
            "system_id": eid, "name": name, "organization": org, "site_key": site,
            "official_website": docs[0][1] if docs else None,
            "documentation_url": (official and SEED_BY_ID[official[0]["source_id"]]["url"]) or _prefer(docs, ["S20", "S01", "S02", "S03", "S06", "S07", "S08", "S04"]),
            "repository_url": _prefer(repos_, ["S06", "S02", "S20", "S01", "S04"]),
            "storybook_url": _prefer(sb, ["S04", "S02"]),
            "design_resource_url": _prefer(fig, ["S01"]),
            "supported_frameworks": sorted(frameworks),
            "framework_evidence": {f: sorted(s) for f, s in frameworks.items()},
            "supported_platforms": [],
            "styling_strategy": _adele(adele, ["CSS", "CSS in JS"]),
            "token_architecture": _adele(adele, ["design tokens"]) or ("snapshot published by designsystems.one" if one.get("breakdown", {}) and (one.get("breakdown") or {}).get("tokenSnapshot") else None),
            "theme_support": None,
            "accessibility_documentation": _adele(adele, ["accessibility guidelines"]) or ("foundation page listed (Surf)" if any(f.get("name", "").lower().startswith("accessib") for f in surf.get("foundations", []) or []) else None),
            "localization_support": None,
            "governance_documentation": ((one.get("breakdown") or {}).get("governance")) if one else None,
            "contribution_model": None,
            "license": None,
            "release_information": None,
            "documentation_coverage": {
                "surf_foundations_claimed": surf.get("foundations_count_claimed"), "surf_components_claimed": surf.get("components_count_claimed"),
                "surf_component_links": len(surf.get("components") or []), "storybook_component_count": sbk.get("component_count"),
                "adele_attributes": {k: v for k, v in adele.items() if k not in ("cell_links", "adele_detail_url")} or None,
            },
            "ai_readiness": (one.get("ai_ready") or {}).get("score") if one else None,
            "sources": sorted({m["source_id"] for m in members}),
            "source_count": len({m["source_id"] for m in members}),
            "source_record_ids": sorted(m["record_id"] for m in members),
            "evidence_urls": sorted({m["source_url"] for m in members}),
            "deprecated_flag": any("deprecated" in (m.get("tags") or []) for m in members),
            "verification_status": "verified" if official else ("partially_verified" if len({m['source_id'] for m in members}) >= 2 else "unverified"),
            "verification_basis": "official documentation inspected (S11–S16)" if official else "independent directory listings only; official docs not inspected",
            "conflicts": {},
        }
        if len({canonical_url(v) for _, v in docs}) > 1:
            ent["conflicts"]["documentation_url"] = sorted({f"{s}: {v}" for s, v in docs})
        if len({o for o in org_votes}) > 1:
            ent["conflicts"]["organization"] = dict(org_votes)
        if len(name_votes) > 1:
            ent["aliases"] = sorted(name_votes)
        if any(m["normalized_content"].get("source_attributes", {}).get("ai_ready") for m in members):
            ent["ai_ready_signals"] = {s["key"]: s["status"] for s in ((one.get("ai_ready") or {}).get("evidence") or {}).get("signals", [])}
        entities.append(ent)
        for m in members:
            m["duplicate_group_id"] = eid
            m["relationships"].append({"type": "canonical_entity", "target": eid})
        if ent["conflicts"]:
            review.append({"type": "system_field_conflict", "entity": eid, "details": ent["conflicts"]})
    # Same organisation, different site keys → possible duplicates for manual review (never auto-merged)
    by_org = defaultdict(list)
    for e in entities:
        if e["organization"]:
            by_org[slugify(e["organization"])].append(e)
    for org, es in by_org.items():
        if len(es) > 1:
            review.append({"type": "possible_duplicate_system", "organization": es[0]["organization"],
                           "entities": [{"system_id": e["system_id"], "name": e["name"], "site": e["site_key"]} for e in es],
                           "reason": "Same organisation name with different documentation hosts; may be distinct systems or moved docs."})
    return sorted(entities, key=lambda e: (-e["source_count"], e["name"].lower())), review


def _prefer(vals, order):
    for s in order:
        for sid, v in vals:
            if sid == s:
                return v
    return vals[0][1] if vals else None


def _adele(attrs, keys):
    vals = [f"{k}: {attrs[k]}" for k in keys if attrs.get(k) and attrs[k].lower() not in ("no data", "")]
    return "; ".join(vals) + " (Adele)" if vals else None


def dedupe_other(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    review = []
    # Components: same canonical system + family → duplicate group (kept as separate records)
    sys_of = {r["record_id"]: r.get("duplicate_group_id") for r in records if r["record_type"] in ("system", "tool")}
    groups = defaultdict(list)
    for r in records:
        if r["record_type"] != "component":
            continue
        ent = next((sys_of.get(x["target"]) for x in r["relationships"] if x["type"] in ("documented_by_system", "part_of") and sys_of.get(x["target"])), None)
        key = (ent or f"lib:{slugify(r.get('design_system') or '')}", slugify(r["normalized_content"].get("component_name") or r["title"]))
        groups[key].append(r)
        r["system_entity"] = ent
    for (ent, name), members in groups.items():
        if len(members) > 1:
            gid = f"dcmp:{slugify(str(ent))}:{name}"
            for m in members:
                m["duplicate_group_id"] = gid
            if len({m["source_id"] for m in members}) == 1 and len(members) > 1:
                review.append({"type": "same_source_component_duplicate", "group": gid, "records": [m["record_id"] for m in members]})
    # Resources: same destination URL
    rg = defaultdict(list)
    for r in records:
        if r["record_type"] == "resource":
            d = r["normalized_content"].get("destination_canonical")
            if d:
                rg[d].append(r)
    for d, members in rg.items():
        if len(members) > 1:
            gid = "dres:" + hashlib.sha1(d.encode()).hexdigest()[:12]
            for m in members:
                m["duplicate_group_id"] = gid
                m["normalized_content"]["referenced_by_sources"] = sorted({x["source_id"] for x in members})
    return review


# ───────────────────────────── validate ─────────────────────────────
REQUIRED = ["record_id", "record_type", "title", "primary_category", "source_id", "source_url", "extraction_method", "confidence", "verification_status"]
ENUMS = {"record_type": {"system", "component", "token", "pattern", "guideline", "tool", "specification", "repository", "resource", "comparison"},
         "confidence": {"high", "medium", "low"}, "verification_status": {"verified", "partially_verified", "unverified"},
         "source_status": {"official", "community", "third_party", "unknown", "derived"},
         "extraction_method": {"html", "browser", "api", "repository", "document", "manual", "sitemap"}}


def validate(records: List[Dict[str, Any]], entities: List[Dict[str, Any]]) -> Dict[str, Any]:
    issues, seen = [], {}
    for r in records:
        rid = r.get("record_id")
        if rid in seen:
            n = 2
            while f"{rid}~{n}" in seen:
                n += 1
            issues.append({"type": "duplicate_record_id_resolved", "record_id": rid, "new_id": f"{rid}~{n}"})
            r["record_id"] = f"{rid}~{n}"
        seen[r["record_id"]] = r
        for f in REQUIRED:
            if not r.get(f):
                issues.append({"type": "missing_required", "record_id": r["record_id"], "field": f})
        for f, allowed in ENUMS.items():
            if r.get(f) is not None and r[f] not in allowed:
                issues.append({"type": "invalid_enum", "record_id": r["record_id"], "field": f, "value": r[f]})
        u = r.get("source_url") or ""
        if not re.match(r"^https?://[^\s/$.?#].[^\s]*$", u):
            issues.append({"type": "invalid_url", "record_id": r["record_id"], "url": u})
    ent_ids = {e["system_id"] for e in entities}
    dangling = 0
    for r in records:
        for rel in r.get("relationships", []):
            t = rel.get("target")
            if t not in seen and t not in ent_ids:
                dangling += 1
                issues.append({"type": "dangling_relationship", "record_id": r["record_id"], "target": t})
    return {"issue_count": len(issues), "issues": issues[:500], "dangling_relationships": dangling,
            "by_type": dict(Counter(i["type"] for i in issues))}


# ───────────────────────────── analysis helpers ─────────────────────────────
LIBS = [("S11", "shadcn/ui"), ("S12", "Radix Primitives"), ("S13", "Base UI"), ("S14", "React Aria"), ("S15", "Mantine"), ("S16", "Ant Design")]
STATE_PROP = re.compile(r"^(default)?(open|opened|value|checked|selected|selectedKeys?|selectedKey|isOpen|isSelected|expanded|expandedKeys|activeKey|ActiveKey|pressed)$", re.I)
# State-related callbacks only (excludes inherited DOM/media/interaction events such as onVolumeChange, onHoverChange)
HANDLER_PROP = re.compile(r"^on((Open|Value|Checked|Pressed|Selection|Expanded|Active|InputValue|Input|Tab|Search)?Change|Close|Cancel|Ok|Select|Expand|OpenChangeComplete)$")


def library_stats(records):
    out = {}
    for sid, lib in LIBS:
        comps = [r for r in records if r["source_id"] == sid and r["record_type"] == "component"]
        toks = [r for r in records if r["source_id"] == sid and r["record_type"] == "token"]
        guides = [r for r in records if r["source_id"] == sid and r["record_type"] == "guideline"]
        tool = next((r for r in records if r["source_id"] == sid and r["record_type"] == "tool"), None)
        nc = tool["normalized_content"] if tool else {}
        props = sum(r["normalized_content"].get("props_count", 0) for r in comps)
        out[sid] = {
            "library": lib, "version": tool.get("source_version") if tool else None, "library_type": nc.get("library_type"),
            "frameworks": nc.get("frameworks"), "technologies": nc.get("technologies"),
            "components": len(comps), "with_props": sum(1 for r in comps if r["normalized_content"].get("props_count")),
            "props_total": props, "with_keyboard": sum(1 for r in comps if r["normalized_content"].get("keyboard")),
            "with_a11y_section": sum(1 for r in comps if r["normalized_content"].get("accessibility_notes")),
            "with_anatomy": sum(1 for r in comps if r["normalized_content"].get("has_anatomy_section")),
            "tokens": len(toks), "token_formats": sorted({t["normalized_content"].get("source_format") for t in toks if t["normalized_content"].get("source_format")}),
            "guides": len(guides), "families": sorted({r["normalized_content"].get("family") for r in comps if r["normalized_content"].get("family")}),
            "source_url": tool["source_url"] if tool else SEED_BY_ID[sid]["url"],
        }
    return out


def api_patterns(records, families=("Dialog", "Tabs", "Checkbox", "Select", "Switch", "Accordion", "Slider", "Combobox")):
    table = {}
    for fam in families:
        row = {}
        for sid, lib in LIBS:
            comps = [r for r in records if r["source_id"] == sid and r["record_type"] == "component" and r["normalized_content"].get("family") == fam]
            state, handlers, ex = set(), set(), []
            for c in comps:
                for sub in c["normalized_content"].get("subcomponents", []):
                    for p in sub.get("props", []):
                        n = (p.get("name") or "").strip("`").split("?")[0]
                        if STATE_PROP.match(n):
                            state.add(n)
                        elif HANDLER_PROP.match(n):
                            handlers.add(n)
                ex.append(c["record_id"])
            row[lib] = {"components": [c["normalized_content"]["component_name"] for c in comps][:6], "state_props": sorted(state)[:10],
                        "change_handlers": sorted(handlers)[:8], "evidence": ex[:6]}
        table[fam] = row
    return table


def family_matrix(records):
    m = defaultdict(dict)
    for sid, lib in LIBS:
        for r in records:
            if r["source_id"] == sid and r["record_type"] == "component" and r["normalized_content"].get("family"):
                m[r["normalized_content"]["family"]].setdefault(lib, []).append(r["normalized_content"]["component_name"])
    return m


# ───────────────────────────── export helpers ─────────────────────────────
def write_csv(path: Path, rows: List[Dict[str, Any]], cols: List[str]) -> None:
    with open(path, "w", newline="", encoding="utf8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: (json.dumps(r.get(c), ensure_ascii=False) if isinstance(r.get(c), (list, dict)) else r.get(c)) for c in cols})


def chunks_for(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for r in records:
        nc = r.get("normalized_content") or {}
        base = {"parent_record_id": r["record_id"], "source_id": r["source_id"], "source_url": r["source_url"], "category": r["primary_category"],
                "version": r.get("source_version"), "entity_ids": [x for x in [r.get("duplicate_group_id"), r.get("system_entity")] if x]}
        head = f"{r['title']} [{r['record_type']}, {r.get('category_name')}]"
        if r["record_type"] == "component":
            text = [head, r.get("summary") or ""]
            fam = nc.get("family")
            if fam:
                text.append(f"Family: {fam}. Library: {nc.get('library')}. Docs: {nc.get('documentation_url')}")
            out.append({**base, "chunk_id": r["record_id"] + "#overview", "section_title": "Overview", "content": "\n".join(text)})
            for sub in nc.get("subcomponents", []):
                if not sub.get("props"):
                    continue
                lines = [f"{nc.get('library')} {nc.get('component_name')} — {sub['name']} props:"]
                for p in sub["props"][:60]:
                    lines.append(f"- {p.get('name')} ({p.get('type') or '?'}; default {p.get('default') or '—'}): {excerpt(p.get('description'), 200) or ''}")
                out.append({**base, "chunk_id": r["record_id"] + "#props-" + slugify(sub["name"]), "section_title": f"API: {sub['name']}", "content": "\n".join(lines)})
            if nc.get("keyboard"):
                lines = [f"{nc.get('library')} {nc.get('component_name')} keyboard interactions:"] + [f"- {k.get('keys')}: {k.get('description')}" for k in nc["keyboard"][:40]]
                out.append({**base, "chunk_id": r["record_id"] + "#keyboard", "section_title": "Keyboard interaction", "content": "\n".join(lines)})
            if nc.get("accessibility_notes"):
                lines = [f"{nc.get('library')} {nc.get('component_name')} accessibility notes:"] + [f"- [{a['section']}] {a['text']}" for a in nc["accessibility_notes"][:8]]
                out.append({**base, "chunk_id": r["record_id"] + "#a11y", "section_title": "Accessibility", "content": "\n".join(lines)})
        else:
            parts = [head, r.get("summary") or ""]
            if r["record_type"] == "token":
                parts.append(f"{nc.get('token_path')} = {nc.get('raw_value')} (type {nc.get('token_type')}, theme {nc.get('theme')}, {nc.get('source_format')}). {nc.get('description') or ''}")
            elif r["record_type"] == "guideline" and nc.get("kind") == "checklist_item":
                parts.append(f"Requirement: {nc.get('requirement')}. Section: {nc.get('section')}. Source wording: {nc.get('source_wording') or ''}")
            elif r["record_type"] in ("resource",):
                parts.append(f"Link: {nc.get('destination_url')}")
            out.append({**base, "chunk_id": r["record_id"] + "#main", "section_title": r.get("source_section") or "Main", "content": "\n".join(p for p in parts if p)})
    return out


# ───────────────────────────── build ─────────────────────────────
def build() -> Dict[str, Any]:
    OUT.mkdir(parents=True, exist_ok=True)
    records, coverage = load_stage()
    print(f"[build] loaded {len(records)} records from {sum(1 for c in coverage.values() if c.get('crawl_status') != 'not_run')} sources", flush=True)
    normalize(records)
    categorize(records)
    entities, review = dedupe_systems(records)
    review += dedupe_other(records)
    report = validate(records, entities)
    manifest = MANIFEST.entries()
    from . import reports
    reports.write_all(records, entities, coverage, review, report, manifest)
    return report
