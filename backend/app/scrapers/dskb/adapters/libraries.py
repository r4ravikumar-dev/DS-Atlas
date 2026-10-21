"""Adapters for component libraries S11–S16. Prefer each project's official machine-readable
documentation (llms.txt Markdown, registries, published package metadata) over scraping rendered HTML."""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

from ..core import (FETCHER, GITHUB, classify_table, excerpt, make_record, md_sections, md_tables, norm_prop,
                    npm_latest, slugify)
from ..sources import ALIAS_TO_FAMILY
from .common import fetch_many, new_coverage, probe_seed

LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)(?::\s*(.*))?")
A11Y_WORDS = ("accessib", "keyboard", "aria", "screen reader", "focus")


def _done(cov, records):
    cov["records_emitted"] = len(records)
    return {"records": records, "coverage": cov}


def family_of(name: str) -> Optional[str]:
    n = re.sub(r"([a-z])([A-Z])", r"\1 \2", name).lower().replace("-", " ").strip()
    return ALIAS_TO_FAMILY.get(n) or ALIAS_TO_FAMILY.get(n.replace(" ", "")) or ALIAS_TO_FAMILY.get(n.rstrip("s"))


def llms_links(text: str, base: str) -> List[Tuple[str, str, Optional[str], str]]:
    """Return (title, absolute_url, description, section_heading) for every list link in an llms.txt."""
    out, section = [], ""
    for line in text.splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
        m = LINK.search(line) if line.lstrip().startswith(("-", "*")) else None
        if m:
            out.append((m.group(1).strip(), urljoin(base, m.group(2)), (m.group(3) or "").strip() or None, section))
    return out


def extract_component_md(md: str) -> Dict[str, Any]:
    """Generic structured extraction from component documentation Markdown."""
    front: Dict[str, str] = {}
    fm = re.match(r"^---\s*\n(.*?)\n---\s*\n", md, re.S)
    if fm:
        for line in fm.group(1).splitlines():
            m = re.match(r"^(\w+):\s*(.+)$", line)
            if m:
                front[m.group(1)] = m.group(2).strip().strip("'\"")
        md = md[fm.end():]
    secs = md_sections(md)
    title = front.get("title") or next((s["title"] for s in secs if s["level"] == 1), None)
    intro = front.get("description") or front.get("subtitle") or ""
    if intro:
        secs_for_intro: List[Dict[str, Any]] = []
    else:
        secs_for_intro = secs
    for s in secs_for_intro:
        if s["level"] <= 1:
            body = re.sub(r"```.*?```", "", s["body"], flags=re.S)
            body = re.sub(r"^\s*(import|export) .*$", "", body, flags=re.M)
            paras = [p.strip() for p in body.split("\n\n") if p.strip() and not p.strip().startswith(("|", "<", "!", "{"))]
            if paras:
                intro = paras[0]
                break
    subs: Dict[str, Dict[str, Any]] = {}
    keyboard, a11y, examples, styles_api, css_vars = [], [], [], [], []
    for s in secs:
        path = s["path"]
        low = " ".join(path).lower()
        if s["level"] in (2, 3) and not any(k in s["title"].lower() for k in ("api", "props", "demo", "tailwind", "css modules", "usage")):
            examples.append(s["title"])
        if any(w in low for w in A11Y_WORDS) and s["body"].strip():
            a11y.append({"section": " > ".join(path), "text": excerpt(re.sub(r"```.*?```", " ", s["body"], flags=re.S), 500)})
        for t in md_tables(s["body"]):
            kind = classify_table(t["header"])
            if kind == "props":
                owner = s["title"]
                if owner.lower() in ("props", "api", "properties", "component props", "api reference") and len(path) > 1:
                    owner = path[-2]
                sub = subs.setdefault(owner, {"name": owner, "props": [], "data_attributes": [], "css_variables": []})
                sub["props"].extend(p for p in (norm_prop(r) for r in t["rows"]) if p["name"])
            elif kind == "keyboard":
                for r in t["rows"]:
                    vals = list(r.values())
                    keyboard.append({"keys": vals[0] if vals else None, "description": vals[1] if len(vals) > 1 else None, "section": " > ".join(path)})
            elif kind == "data_attributes":
                sub = subs.setdefault(s["title"] if len(path) < 2 else path[-2] if s["title"].lower().startswith("data") else s["title"],
                                      {"name": s["title"], "props": [], "data_attributes": [], "css_variables": []})
                sub["data_attributes"].extend({"attribute": list(r.values())[0], "description": list(r.values())[-1]} for r in t["rows"] if r)
            elif kind == "css_variables":
                css_vars.extend({"variable": list(r.values())[0], "description": list(r.values())[-1]} for r in t["rows"] if r)
            elif kind == "styles_api":
                styles_api.extend({"selector": list(r.values())[0], "description": list(r.values())[-1]} for r in t["rows"] if r)
    # Keyboard info written as definition lists/bullets (e.g. "- `Space` - opens …")
    for s in secs:
        if "keyboard" in s["title"].lower():
            for line in s["body"].splitlines():
                m = re.match(r"\s*[-*]\s*(`[^`]+`(?:\s*[+/,]\s*`[^`]+`)*)\s*[-–:]\s*(.+)", line)
                if m:
                    keyboard.append({"keys": m.group(1).replace("`", ""), "description": m.group(2).strip(), "section": " > ".join(s["path"])})
    # Mantine-style preamble: "Package: … Import: … Description: …" → keep the description only
    m = re.search(r"Description:\s*(.+)", intro or "")
    if m and re.match(r"\s*(Package|Import):", intro or ""):
        intro = m.group(1).strip()
    props_total = sum(len(v["props"]) for v in subs.values())
    return {
        "doc_title": title, "description": intro or None, "subcomponents": list(subs.values()), "props_count": props_total,
        "keyboard": keyboard, "accessibility_notes": a11y[:12], "examples": examples[:40], "styles_api": styles_api,
        "css_variables": css_vars, "section_outline": [" > ".join(s["path"]) for s in secs if s["level"] and s["level"] <= 3][:80],
        "has_anatomy_section": any("anatomy" in s["title"].lower() for s in secs),
    }


def component_record(sid: str, lib: str, name: str, *, url: str, md_url: Optional[str], data: Dict[str, Any], version: Optional[str],
                     category_hint: Optional[str] = None, frameworks=None, technologies=None, kind: str = "component",
                     extraction_method="document", key: Optional[str] = None) -> Dict[str, Any]:
    rec = make_record("component", sid, key or name, f"{lib}: {name}", summary=excerpt(data.get("description"), 500),
                      primary_category="C05", source_url=md_url or url, extraction_method=extraction_method,
                      source_status="official", source_version=version)
    rec["design_system"] = lib
    rec["frameworks"] = frameworks or ["React"]
    rec["technologies"] = technologies or []
    fam = family_of(name)
    rec["normalized_content"] = {"component_name": name, "library": lib, "family": fam, "documentation_url": url,
                                 "markdown_url": md_url, "detail_level": "api" if data.get("props_count") else "doc",
                                 "library_category": category_hint, "component_kind": kind, **data}
    sec = ["C04"]
    if data.get("keyboard") or data.get("accessibility_notes"):
        sec.append("C07")
    rec["secondary_categories"] = sec
    rec["tags"] = [f"library:{slugify(lib)}"] + ([f"family:{slugify(fam)}"] if fam else [])
    rec["evidence_excerpt"] = excerpt(data.get("description"), 300)
    rec["confidence"] = "high"
    rec["verification_status"] = "verified"
    return rec


def guide_record(sid: str, lib: str, title: str, url: str, md: str, version: Optional[str], category: str) -> Dict[str, Any]:
    secs = md_sections(md)
    body = " ".join(re.sub(r"```.*?```", " ", s["body"], flags=re.S) for s in secs[:3])
    rec = make_record("guideline", sid, f"guide-{urlparse(url).path.strip('/')}", f"{lib}: {title}", summary=excerpt(re.sub(r"<[^>]+>", " ", body), 500),
                      primary_category=category, source_url=url, extraction_method="document", source_status="official",
                      source_version=version)
    rec["design_system"] = lib
    rec["normalized_content"] = {"kind": "library_documentation_page", "outline": [" > ".join(s["path"]) for s in secs if s["level"] and s["level"] <= 3][:60],
                                 "code_examples": md.count("```") // 2}
    rec["confidence"] = "high"
    rec["verification_status"] = "verified"
    return rec


def _guide_category(title: str) -> str:
    t = title.lower()
    for keys, cat in ((("accessib", "keyboard", "focus", "rtl", "right-to-left"), "C07"), (("theme", "theming", "dark", "color scheme", "colors"), "C10"),
                      (("token", "variable"), "C03"), (("typograph", "spacing", "breakpoint", "icon", "motion", "animation", "layout"), "C02"),
                      (("ssr", "server", "next", "vite", "install", "cli", "typescript", "testing", "styling", "css", "tailwind", "bundle", "performance"), "C09"),
                      (("migrat", "changelog", "release", "version", "contribut"), "C08"), (("form", "validation"), "C06"), (("llm", "mcp", "ai", "agent"), "C13")):
        if any(k in t for k in keys):
            return cat
    return "C09"


def _lib_meta_record(sid: str, lib: str, url: str, version: Optional[str], content: Dict[str, Any], summary: str) -> Dict[str, Any]:
    rec = make_record("tool", sid, f"library-{lib}", lib, summary=summary, primary_category="C09", source_url=url,
                      extraction_method="document", source_status="official", source_version=version)
    rec["design_system"] = lib
    rec["normalized_content"] = {"kind": "component_library", **content}
    rec["confidence"] = "high"
    rec["verification_status"] = "verified"
    return rec


def _llms_pipeline(seed, *, lib: str, llms_url: str, npm_pkg: str, is_component, is_guide, frameworks, technologies,
                   library_type: str, philosophy: str, workers: int = 1, max_guides: int = 60) -> Dict[str, Any]:
    sid = seed["source_id"]
    cov = new_coverage(seed)
    cov["extraction_method"] = f"official llms.txt index ({llms_url}) → per-page Markdown"
    cov["provides"] = "original"
    records: List[Dict[str, Any]] = []
    probe_seed(seed, cov)
    version = npm_latest(npm_pkg, sid)
    cov["version_context"] = {"npm_package": npm_pkg, "npm_latest": version, "note": "Docs read at the same time; assumed to describe the latest release."}
    idx = FETCHER.get(llms_url, source_id=sid, parent=seed["url"], depth=1)
    cov["pages_attempted"] += 1
    if not idx or not idx.ok:
        cov["errors"].append("llms.txt unavailable")
        return _done(cov, records)
    cov["pages_ok"] += 1
    links = llms_links(idx.text, idx.final_url)
    comps = [(t, u, d, s) for t, u, d, s in links if is_component(t, u, s)]
    guides = [(t, u, d, s) for t, u, d, s in links if not is_component(t, u, s) and is_guide(t, u, s)][:max_guides]
    pages = fetch_many([(u, idx.final_url, 2) for _, u, _, _ in comps + guides], sid, cov, workers=workers)
    for t, u, d, s in comps:
        r = pages.get(u)
        if not r or not r.ok or "markdown" not in (r.headers.get("content-type") or "text/markdown") and r.text.lstrip().startswith("<"):
            continue
        data = extract_component_md(r.text)
        if not data["description"] and d:
            data["description"] = d
        name = (data["doc_title"] or t).strip()
        html_url = re.sub(r"\.md$", "", u.replace("/llms/", "/"))
        rec = component_record(sid, lib, name, url=html_url, md_url=u, data=data, version=version, category_hint=s,
                               frameworks=frameworks, technologies=technologies, key=u.rsplit("/", 1)[-1][:-3])
        records.append(rec)
    for t, u, d, s in guides:
        r = pages.get(u)
        if r and r.ok and not r.text.lstrip().startswith("<"):
            records.append(guide_record(sid, lib, t, u, r.text, version, _guide_category(t + " " + s)))
    comp_recs = [r for r in records if r["record_type"] == "component"]
    meta = _lib_meta_record(sid, lib, seed["url"], version, {
        "library_type": library_type, "philosophy_summary": philosophy, "frameworks": frameworks, "technologies": technologies,
        "component_count_extracted": len(comp_recs), "components_with_props": sum(1 for r in comp_recs if r["normalized_content"]["props_count"]),
        "components_with_keyboard_docs": sum(1 for r in comp_recs if r["normalized_content"]["keyboard"]),
        "llms_index_links": len(links), "npm_package": npm_pkg,
    }, philosophy)
    for r in comp_recs:
        r["relationships"].append({"type": "part_of", "target": meta["record_id"]})
    records.insert(0, meta)
    cov["items_found"] = len(comp_recs)
    cov["coverage_notes"].append({"llms_links": len(links), "component_pages": len(comps), "guide_pages": len(guides)})
    return _done(cov, records)


# ═════════════════════════════ S13 Base UI ═════════════════════════════
def run_baseui(seed):
    return _llms_pipeline(
        seed, lib="Base UI", llms_url="https://base-ui.com/llms.txt", npm_pkg="@base-ui/react",
        is_component=lambda t, u, s: "/react/components/" in u, is_guide=lambda t, u, s: "/react/" in u,
        frameworks=["React"], technologies=["TypeScript", "Headless"], library_type="headless_primitives",
        philosophy="Unstyled, composable React components; styling-agnostic (Tailwind, CSS Modules, CSS-in-JS) per its llms.txt.")


# ═════════════════════════════ S14 React Aria ═════════════════════════════
def run_reactaria(seed):
    out = _llms_pipeline(
        seed, lib="React Aria", llms_url="https://react-aria.adobe.com/llms.txt", npm_pkg="react-aria-components",
        is_component=lambda t, u, s: bool(re.match(r"https://react-aria\.adobe\.com/[A-Z][A-Za-z]+\.md$", u)),
        is_guide=lambda t, u, s: bool(re.match(r"https://react-aria\.adobe\.com/[a-z][\w-]+\.md$", u)),
        frameworks=["React"], technologies=["TypeScript", "Headless", "Hooks"], library_type="headless_components_and_hooks",
        philosophy="Unstyled components and hooks with built-in behaviour, accessibility and internationalisation.")
    out["coverage"]["coverage_notes"].append("Seed URL react-spectrum.adobe.com/react-aria/ resolves to react-aria.adobe.com; extraction used the new host's llms.txt.")
    return out


# ═════════════════════════════ S15 Mantine ═════════════════════════════
MANTINE_COMP_SECTIONS = {"Core", "Dates", "Charts", "Schedule", "Code-highlight", "X"}
MANTINE_NON_COMPONENTS = {"Get started", "Getting started", "Mantine extensions", "Events data", "Recurring events"}


def run_mantine(seed):
    out = _llms_pipeline(
        seed, lib="Mantine", llms_url="https://mantine.dev/llms.txt", npm_pkg="@mantine/core",
        is_component=lambda t, u, s: s in MANTINE_COMP_SECTIONS and t not in MANTINE_NON_COMPONENTS,
        is_guide=lambda t, u, s: s in ("Theming", "Styles", "Guides", "FAQ", "Form") or t in MANTINE_NON_COMPONENTS,
        frameworks=["React"], technologies=["TypeScript", "CSS Modules", "CSS variables", "PostCSS"], library_type="styled_component_library",
        philosophy="Full-featured styled React components and hooks themed via a theme object and CSS variables.", max_guides=90)
    # Tokens: CSS variables list page
    recs, cov = out["records"], out["coverage"]
    u = "https://mantine.dev/llms/styles-css-variables-list.md"
    r = FETCHER.get(u, source_id="S15", depth=2)
    if r and r.ok:
        n = 0
        version = cov["version_context"].get("npm_latest")
        for s in md_sections(r.text):
            for line in s["body"].splitlines():
                m = re.match(r"\s*(--mantine-[\w-]+)\s*:\s*([^;]+);", line)
                if m:
                    recs.append(_token("S15", "Mantine", m.group(1), m.group(2).strip(), u, s, version,
                                       theme="dark" if "dark" in " ".join(s["path"]).lower() else "light" if "light" in " ".join(s["path"]).lower() else None))
                    n += 1
            for t in md_tables(s["body"]):
                for row in t["rows"]:
                    vals = list(row.values())
                    if vals and vals[0].startswith("--mantine"):
                        recs.append(_token("S15", "Mantine", vals[0], vals[1] if len(vals) > 1 else None, u, s, version))
                        n += 1
        cov["coverage_notes"].append({"css_variable_tokens": n})
    out["coverage"]["records_emitted"] = len(recs)
    return out


def _token(sid, lib, name, value, url, sec, version, theme=None, ttype=None, desc=None, path=None, component=None, fmt="CSS custom property"):
    from ..core import sha256 as _sha
    disamb = _sha(f"{' > '.join(sec['path']) if sec else ''}|{value}".encode())[:6]
    t = make_record("token", sid, f"{path or name}-{theme or 'default'}-{disamb}", name, primary_category="C03", source_url=url,
                    extraction_method="document", source_status="official", source_version=version)
    t["design_system"] = lib
    t["source_section"] = " > ".join(sec["path"]) if sec else None
    t["normalized_content"] = {"token_name": name, "token_path": path or name, "token_type": ttype or _infer_type(name, value),
                               "raw_value": value, "resolved_value": None, "alias_of": _alias(value), "semantic_role": None,
                               "theme": theme, "platform": "web", "component": component, "description": desc,
                               "deprecated": None, "source_format": fmt, "type_inferred": ttype is None}
    t["confidence"] = "high"
    t["verification_status"] = "verified"
    return t


def _alias(v):
    if not isinstance(v, str):
        return None
    m = re.search(r"var\((--[\w-]+)", v) or re.search(r"\{([\w.-]+)\}", v)
    return m.group(1) if m else None


def _infer_type(name: str, value) -> Optional[str]:
    n, v = name.lower(), str(value or "").lower()
    if re.search(r"color|bg|background|foreground|border-color|fill|stroke", n) or re.match(r"^(#|rgb|hsl|oklch|oklab|lab\()", v):
        return "color"
    if "font-family" in n or "fontfamily" in n:
        return "fontFamily"
    if "font-weight" in n or "fontweight" in n:
        return "fontWeight"
    if "shadow" in n:
        return "shadow"
    if "duration" in n or re.match(r"^\d+m?s$", v):
        return "duration"
    if "line-height" in n or "lineheight" in n:
        return "number"
    if re.match(r"^-?[\d.]+(px|rem|em|%)$", v) or any(k in n for k in ("radius", "spacing", "size", "breakpoint", "width", "height")):
        return "dimension"
    if "z-index" in n or "zindex" in n:
        return "number"
    return None


# ═════════════════════════════ S16 Ant Design ═════════════════════════════
def run_antd(seed):
    out = _llms_pipeline(
        seed, lib="Ant Design", llms_url="https://ant.design/llms.txt", npm_pkg="antd",
        is_component=lambda t, u, s: bool(re.match(r"https://ant\.design/components/[a-z-]+\.md$", u)) and not u.endswith("-cn.md") and not any(x in u for x in ("_util", "overview", "changelog")),
        is_guide=lambda t, u, s: bool(re.search(r"ant\.design/docs/(spec|react)/", u)) and not u.endswith("-cn.md"),
        frameworks=["React"], technologies=["TypeScript", "CSS-in-JS", "Design tokens"], library_type="styled_enterprise_design_system",
        philosophy="Enterprise-class React UI library with a design language and token-based theming (per its llms.txt).", max_guides=120)
    recs, cov = out["records"], out["coverage"]
    # Ant Design specs are pattern guidance → re-type as patterns
    for r in recs:
        if r["record_type"] == "guideline" and "/docs/spec/" in r["source_url"]:
            r["normalized_content"]["kind"] = "design_specification"
            r["primary_category"] = "C06" if any(k in r["title"].lower() for k in ("case", "navigation", "form", "data", "feedback", "message", "button", "visualization")) else "C02"
    # Tokens from the published package metadata (token-meta.json) via jsDelivr, pinned to the npm version
    version = cov["version_context"].get("npm_latest")
    if version:
        u = f"https://cdn.jsdelivr.net/npm/antd@{version}/lib/version/token-meta.json"
        r = FETCHER.get(u, source_id="S16", depth=2)
        cov["pages_attempted"] += 1
        if r and r.ok:
            cov["pages_ok"] += 1
            meta = r.json()
            n = 0
            glob = meta.get("global", {})
            for name, info in glob.items():
                recs.append(_antd_token(name, info, u, version, None))
                n += 1
            for comp, toks in (meta.get("components") or {}).items():
                for info in toks if isinstance(toks, list) else [dict(v, token=k) for k, v in toks.items()]:
                    recs.append(_antd_token(info.get("token") or info.get("name"), info, u, version, comp))
                    n += 1
            cov["coverage_notes"].append({"token_meta_records": n})
            tv = FETCHER.get(f"https://cdn.jsdelivr.net/npm/antd@{version}/lib/version/token.json", source_id="S16", depth=2)
            if tv and tv.ok:
                vals = tv.json()
                used_by: Dict[str, List[str]] = {}
                for comp, v in vals.items():
                    for g in (v.get("global") or []):
                        used_by.setdefault(g, []).append(comp)
                for rec in recs:
                    nc = rec.get("normalized_content", {})
                    if rec["record_type"] != "token" or rec["source_id"] != "S16":
                        continue
                    comp = nc.get("component")
                    if comp:
                        cvals = (vals.get(comp) or {}).get("component") or {}
                        if nc["token_name"] in cvals:
                            nc["raw_value"] = cvals[nc["token_name"]]
                            nc["value_source"] = "lib/version/token.json (default theme algorithm output)"
                    else:
                        nc["used_by_components"] = sorted(used_by.get(nc["token_name"], []))
        else:
            cov["limitations"].append("token-meta.json not available for this version.")
    out["coverage"]["records_emitted"] = len(recs)
    return out


def _is_token(d):
    return isinstance(d, dict) and all(isinstance(v, dict) and ("desc" in v or "type" in v) for v in list(d.values())[:3])


def _antd_token(name, info, url, version, component):
    t = make_record("token", "S16", f"{component or 'global'}-{name}", name, primary_category="C03", source_url=url,
                    extraction_method="api", source_status="official", source_version=version)
    t["design_system"] = "Ant Design"
    t["normalized_content"] = {"token_name": name, "token_path": f"{component}.{name}" if component else name,
                               "token_type": info.get("type"), "raw_value": None, "resolved_value": None, "alias_of": None,
                               "semantic_role": info.get("source"), "theme": "default", "platform": "web", "component": component,
                               "description": info.get("descEn") or info.get("desc"), "display_name": info.get("nameEn") or None,
                               "description_zh": info.get("desc"),
                               "deprecated": None, "source_format": "antd token-meta.json (published package)"}
    if info.get("descEn"):
        t["normalized_content"]["description"] = info["descEn"]
    t["confidence"] = "high"
    t["verification_status"] = "verified"
    t["secondary_categories"] = ["C10"]
    return t


# ═════════════════════════════ S11 shadcn/ui ═════════════════════════════
def run_shadcn(seed):
    sid = "S11"
    cov = new_coverage(seed)
    cov["extraction_method"] = "official registry index (/r/index.json) + registry items + docs Markdown (.md) + llms.txt"
    cov["provides"] = "original"
    records: List[Dict[str, Any]] = []
    probe_seed(seed, cov)
    version = npm_latest("shadcn", sid)
    cov["version_context"] = {"npm_package": "shadcn (CLI)", "npm_latest": version, "registry_style": "new-york-v4"}
    idx = FETCHER.get("https://ui.shadcn.com/r/index.json", source_id=sid, parent=seed["url"], depth=1)
    cov["pages_attempted"] += 1
    if not idx or not idx.ok:
        return _done(cov, records)
    cov["pages_ok"] += 1
    items = [i for i in idx.json() if i.get("type") == "registry:ui"]
    md_urls = [f"https://ui.shadcn.com/docs/components/radix/{i['name']}.md" for i in items]
    reg_urls = [f"https://ui.shadcn.com/r/styles/new-york-v4/{i['name']}.json" for i in items]
    pages = fetch_many([(u, idx.final_url, 2) for u in md_urls + reg_urls], sid, cov)
    for i, mdu, regu in zip(items, md_urls, reg_urls):
        mr, rr = pages.get(mdu), pages.get(regu)
        data = extract_component_md(mr.text) if mr and mr.ok and not mr.text.lstrip().startswith("<") else {"description": None, "props_count": 0, "keyboard": [], "accessibility_notes": [], "subcomponents": []}
        reg = rr.json() if rr and rr.ok else {}
        files = reg.get("files", [])
        src = files[0]["content"] if files and files[0].get("content") else ""
        variants = {}
        m = re.search(r"variants:\s*\{(.*?)\n\s{4}\},\n\s{4}defaultVariants", src, re.S)
        if m:
            for vm in re.finditer(r"\n\s{6}(\w+):\s*\{(.*?)\n\s{6}\}", m.group(1), re.S):
                variants[vm.group(1)] = re.findall(r"\n\s{8}\"?([\w-]+)\"?:", vm.group(2))
        data.update({"registry_name": i["name"], "registry_dependencies": reg.get("registryDependencies", []),
                     "npm_dependencies": reg.get("dependencies", []), "files": [f.get("path") for f in files],
                     "variants_from_source": variants or None,
                     "exports": sorted(set(re.findall(r"^export\s*\{([^}]+)\}", src, re.M)[0].replace("\n", "").replace(" ", "").split(","))) if re.search(r"^export\s*\{", src, re.M) else [],
                     "base_links": (i.get("meta") or {}).get("links")})
        data["component_kind"] = "recipe"
        name = data.get("doc_title") or i["name"].replace("-", " ").title()
        rec = component_record(sid, "shadcn/ui", name, url=f"https://ui.shadcn.com/docs/components/radix/{i['name']}", md_url=mdu if mr and mr.ok else None,
                               data=data, version=version, frameworks=["React"], technologies=["Tailwind CSS", "Radix UI / Base UI", "class-variance-authority"],
                               kind="recipe")
        rec["notes"].append("shadcn/ui components are copy-in source recipes built on Radix UI or Base UI primitives; props largely pass through to the underlying primitive.")
        if reg:
            rec["normalized_content"]["source_code_sha256"] = None
        records.append(rec)
    # Theming tokens (CSS variables) from the theming docs page
    th = FETCHER.get("https://ui.shadcn.com/docs/theming.md", source_id=sid, depth=2)
    cov["pages_attempted"] += 1
    if th and th.ok:
        cov["pages_ok"] += 1
        for s in md_sections(th.text):
            for block in re.findall(r"```css[^\n]*\n(.*?)```", s["body"], re.S):
                theme = None
                for line in block.splitlines():
                    if re.match(r"\s*:root", line):
                        theme = "light"
                    elif re.match(r"\s*\.dark", line):
                        theme = "dark"
                    mm = re.match(r"\s*(--[\w-]+)\s*:\s*([^;]+);", line)
                    if mm:
                        records.append(_token(sid, "shadcn/ui", mm.group(1), mm.group(2).strip(), "https://ui.shadcn.com/docs/theming.md", s, version, theme=theme))
        records.append(guide_record(sid, "shadcn/ui", "Theming", "https://ui.shadcn.com/docs/theming.md", th.text, version, "C10"))
    # Docs guides from llms.txt
    ll = FETCHER.get("https://ui.shadcn.com/llms.txt", source_id=sid, depth=1)
    if ll and ll.ok:
        guides = [(t, u) for t, u, d, s in llms_links(ll.text, ll.final_url) if "/docs/" in u and "/components/" not in u and not u.rstrip("/").endswith("/theming")][:30]
        gp = fetch_many([(u + ".md", ll.final_url, 2) for _, u in guides], sid, cov)
        for t, u in guides:
            r = gp.get(u + ".md")
            if r and r.ok and not r.text.lstrip().startswith("<"):
                records.append(guide_record(sid, "shadcn/ui", t, u, r.text, version, _guide_category(t)))
    comps = [r for r in records if r["record_type"] == "component"]
    meta = _lib_meta_record(sid, "shadcn/ui", seed["url"], version, {
        "library_type": "component_recipes (copy-in source)", "frameworks": ["React"],
        "technologies": ["Tailwind CSS", "Radix UI", "Base UI", "CSS variables"], "component_count_extracted": len(comps),
        "registry_items_total": len(idx.json()), "registry_ui_items": len(items)}, "Open-code components distributed through a registry/CLI and owned by the consuming codebase (per its docs).")
    records.insert(0, meta)
    cov["items_found"] = len(comps)
    return _done(cov, records)


# ═════════════════════════════ S12 Radix Primitives ═════════════════════════════
def _radix_tables(src: str, tag: str) -> List[Tuple[str, List[Dict[str, Any]]]]:
    """Parse <Tag data={[ {...}, ... ]} /> JSX blocks into lists of dicts (string fields only)."""
    out = []
    for m in re.finditer(r"<%s\s*\n?\s*data=\{\[(.*?)\]\}" % tag, src, re.S):
        start = m.start()
        heading = re.findall(r"^#{2,4}\s+(.+)$", src[:start], re.M)
        rows = []
        for obj in re.finditer(r"\{(.*?)\n\t\t\}", m.group(1), re.S):
            body = obj.group(1)
            row = {}
            for k in ("name", "type", "typeSimple", "default", "required", "attribute", "values", "cssVariable"):
                mm = re.search(r"\b%s:\s*(\"(?:[^\"\\]|\\.)*\"|'[^']*'|true|false|\[[^\]]*\])" % k, body)
                if mm:
                    v = mm.group(1)
                    row[k] = v.strip("\"'") if v[0] in "\"'" else v
            keys = re.search(r"keys:\s*\[([^\]]*)\]", body)
            if keys:
                row["keys"] = [k.strip().strip("\"'") for k in keys.group(1).split(",") if k.strip()]
            d = re.search(r"description:\s*(\"(?:[^\"\\]|\\.)*\"|\((.*?)\)\s*,?\s*$)", body, re.S)
            if d:
                row["description"] = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", d.group(2) or d.group(1).strip('"'))).strip()
            if row:
                rows.append(row)
        out.append((heading[-1] if heading else "", rows))
    return out


def run_radix(seed):
    sid = "S12"
    cov = new_coverage(seed)
    cov["extraction_method"] = "official docs source (radix-ui/website MDX on GitHub, pinned commit); site has no llms.txt"
    cov["provides"] = "original"
    records: List[Dict[str, Any]] = []
    probe_seed(seed, cov)
    version = npm_latest("radix-ui", sid)
    meta = GITHUB.repo("radix-ui/website", sid)
    cov["pages_attempted"] += 3
    if meta.get("error"):
        cov["errors"].append(f"GitHub: {meta['error']}")
        return _done(cov, records)
    cov["pages_ok"] += 3
    sha = meta["commit_sha"]
    cov["version_context"] = {"npm_package": "radix-ui", "npm_latest": version, "docs_repo": "radix-ui/website", "commit_sha": sha}
    paths = sorted(p for p in meta["paths"] if re.match(r"data/primitives/docs/(components|utilities)/[\w-]+\.mdx$", p))
    # Only the newest version file per component if versioned folders exist
    for p in paths:
        src = GITHUB.raw("radix-ui/website", sha, p, sid)
        cov["pages_attempted"] += 1
        if not src:
            continue
        cov["pages_ok"] += 1
        fm = dict(re.findall(r"^(\w+):\s*(.+)$", src.split("---")[1], re.M)) if src.startswith("---") else {}
        name = fm.get("metaTitle", p.rsplit("/", 1)[-1][:-4].replace("-", " ").title()).strip("'\"")
        desc = fm.get("metaDescription", "").strip("'\"") or None
        subs, kb, da, cssv = [], [], [], []
        for heading, rows in _radix_tables(src, "PropsTable"):
            subs.append({"name": heading, "props": [{"name": r.get("name"), "type": r.get("type"), "default": r.get("default"),
                                                    "description": r.get("description"), "required": r.get("required")} for r in rows],
                         "data_attributes": [], "css_variables": []})
        for heading, rows in _radix_tables(src, "DataAttributesTable"):
            tgt = next((s for s in subs if s["name"] == heading), None)
            items = [{"attribute": r.get("attribute"), "values": r.get("values")} for r in rows]
            if tgt:
                tgt["data_attributes"].extend(items)
            else:
                da.extend(items)
        for heading, rows in _radix_tables(src, "KeyboardTable"):
            kb.extend({"keys": " + ".join(r.get("keys", [])), "description": r.get("description"), "section": heading} for r in rows)
        for heading, rows in _radix_tables(src, "CssVariablesTable"):
            cssv.extend({"variable": r.get("cssVariable"), "description": r.get("description")} for r in rows)
        secs = md_sections(src)
        a11y = [{"section": " > ".join(s["path"]), "text": excerpt(re.sub(r"<[^>]+>", " ", s["body"]), 500)} for s in secs if "accessib" in s["title"].lower()]
        anatomy = re.search(r"## Anatomy.*?```jsx\n(.*?)```", src, re.S)
        data = {"doc_title": name, "description": desc, "subcomponents": subs, "props_count": sum(len(s["props"]) for s in subs),
                "keyboard": kb, "accessibility_notes": a11y, "data_attributes": da, "css_variables": cssv,
                "examples": [s["title"] for s in secs if s["level"] == 3 and "Examples" in " ".join(s["path"])],
                "anatomy": anatomy.group(1).strip() if anatomy else None, "has_anatomy_section": bool(anatomy),
                "aria_pattern_links": sorted(set(re.findall(r"https://www\.w3\.org/WAI/ARIA/apg/[\w/#-]+", src))),
                "section_outline": [" > ".join(s["path"]) for s in secs if s["level"] and s["level"] <= 3][:60]}
        kind = "utility" if "/utilities/" in p else "primitive"
        slug = p.rsplit("/", 1)[-1][:-4]
        rec = component_record(sid, "Radix Primitives", name, url=f"https://www.radix-ui.com/primitives/docs/{'utilities' if kind == 'utility' else 'components'}/{slug}",
                               md_url=GITHUB.blob_url("radix-ui/website", sha, p), data=data, version=version,
                               technologies=["TypeScript", "Headless"], kind=kind, extraction_method="repository")
        rec["source_file_path"] = p
        rec["repository_url"] = "https://github.com/radix-ui/website"
        records.append(rec)
    comps = [r for r in records if r["record_type"] == "component"]
    meta_rec = _lib_meta_record(sid, "Radix Primitives", seed["url"], version, {
        "library_type": "headless_primitives", "frameworks": ["React"], "technologies": ["TypeScript"],
        "component_count_extracted": len(comps), "docs_source": "radix-ui/website@" + sha[:7]},
        "Unstyled, accessible React primitives handling focus management, keyboard navigation and ARIA (per its docs).")
    for r in comps:
        r["relationships"].append({"type": "part_of", "target": meta_rec["record_id"]})
    records.insert(0, meta_rec)
    cov["items_found"] = len(comps)
    cov["limitations"].append("Radix docs are read from the official website repository MDX; rendered pages were not scraped. JSX descriptions are flattened to text.")
    return _done(cov, records)
