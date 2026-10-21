"""Adapters for GitHub-hosted sources: S06–S08 (curated lists), S09 (Style Dictionary),
S10 (DTCG), S19 (Design System Checklist)."""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from ..core import FETCHER, GITHUB, excerpt, make_record, md_sections, md_tables, npm_latest, slugify
from .common import gh_full_name, new_coverage, page_meta, probe_seed, resource_record, system_record

PERMISSIVE = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "CC0-1.0", "CC-BY-4.0", "Unlicense", "W3C"}
MD_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")


def _done(cov, records):
    cov["records_emitted"] = len(records)
    return {"records": records, "coverage": cov}


def _repo_record(sid: str, meta: Dict[str, Any], category: str, readme: Optional[str]) -> Dict[str, Any]:
    full = meta.get("full_name")
    rec = make_record("repository", sid, full, full, summary=meta.get("description"), primary_category=category,
                      source_url=meta.get("html_url") or f"https://github.com/{full}", extraction_method="api",
                      source_status="official" if sid in ("S09", "S10") else "community")
    rec["repository_url"] = meta.get("html_url")
    rec["license"] = meta.get("license")
    rec["source_version"] = meta.get("commit_sha")
    paths = meta.get("paths", [])
    rec["normalized_content"] = {
        k: meta.get(k) for k in ("full_name", "default_branch", "commit_sha", "commit_date", "language", "stars", "forks",
                                 "open_issues", "archived", "pushed_at", "topics", "homepage", "tree_truncated")}
    rec["normalized_content"].update({
        "file_count": len(paths),
        "top_level": sorted({p.split("/")[0] for p in paths})[:60],
        "has_contributing": any(p.lower().endswith("contributing.md") for p in paths),
        "has_changelog": any(p.lower().endswith("changelog.md") for p in paths),
        "readme_headings": [s["title"] for s in md_sections(readme or "") if s["level"] and s["level"] <= 3][:60],
    })
    rec["confidence"] = "high"
    rec["verification_status"] = "verified"
    return rec


def _load_repo(seed, cov, full: str) -> Tuple[Dict[str, Any], Optional[str]]:
    meta = GITHUB.repo(full, seed["source_id"])
    cov["pages_attempted"] += 3
    if meta.get("error"):
        cov["errors"].append(f"GitHub API: {meta['error']}")
        return meta, None
    cov["pages_ok"] += 3
    cov["version_context"] = {"commit_sha": meta.get("commit_sha"), "commit_date": meta.get("commit_date"), "branch": meta.get("default_branch")}
    readme_path = next((p for p in meta["paths"] if p.lower() == "readme.md"), None)
    readme = GITHUB.raw(full, meta["commit_sha"], readme_path, seed["source_id"]) if readme_path else None
    cov["pages_attempted"] += 1
    cov["pages_ok"] += int(bool(readme))
    return meta, readme


# ═════════════════════════════ S06–S08 curated lists ═════════════════════════════
KLAUFEL_CAT = {
    "design systems articles": "C01", "more resources": "C12", "design tools": "C09", "integrations": "C09",
    "accessibility (a11y)": "C07", "design tools articles": "C09", "plugins": "C03", "tools": "C03", "articles": "C03",
    "coding tools": "C09", "styleguides and documentation": "C08", "develop isolated components": "C09",
    "storybook addons": "C09", "pattern libraries articles": "C08", "unit & regression test": "C09", "books": "C01", "talks": "C01",
}


def run_awesome(seed):
    sid = seed["source_id"]
    cov = new_coverage(seed)
    cov["extraction_method"] = "GitHub REST API (metadata, tree) + README at pinned commit"
    cov["provides"] = "links"
    records: List[Dict[str, Any]] = []
    probe_seed(seed, cov)
    full = gh_full_name(seed["url"])
    meta, readme = _load_repo(seed, cov, full)
    if not readme:
        cov["crawl_status"] = "failed_readme"
        return _done(cov, records)
    repo_rec = _repo_record(sid, meta, "C12", readme)
    records.append(repo_rec)
    blob = GITHUB.blob_url(full, meta["commit_sha"], "README.md")

    if sid == "S06":  # alexpate: one table, emoji columns
        for t in md_tables(readme):
            cols = t["header"]
            for row in t["rows"]:
                first = row.get(cols[0], "")
                m = MD_LINK.search(first)
                if not m:
                    continue
                name, url = m.group(1), m.group(2)
                flags = {c: ("👍" in row.get(c, "")) for c in cols[1:] if c and "Source" not in c}
                src_cell = next((row[c] for c in cols if "Source" in c), "")
                src = MD_LINK.search(src_cell)
                rec = system_record(sid, name, name, evidence_url=blob, method="repository", docs_url=url,
                                    repo_url=src.group(2) if src else None, attributes={"public_assets": flags})
                rec["source_file_path"] = "README.md"
                rec["source_version"] = meta["commit_sha"]
                rec["tags"] = ["awesome:alexpate"] + [f"has:{slugify(k)}" for k, v in flags.items() if v]
                rec["relationships"] = [{"type": "listed_in", "target": repo_rec["record_id"]}]
                records.append(rec)
    elif sid == "S08":  # saadeghi: Name | Link
        for t in md_tables(readme):
            for row in t["rows"]:
                name, link = row.get("Name"), row.get("Link")
                if not name or not link:
                    continue
                mm = re.match(r"(.+?)\s+by\s+(.+)$", name)
                sysname, org = (mm.group(1), mm.group(2)) if mm else (name, None)
                link = MD_LINK.search(link).group(2) if MD_LINK.search(link) else link.strip()
                rec = system_record(sid, name, sysname, organization=org, evidence_url=blob, method="repository", docs_url=link)
                rec["source_file_path"] = "README.md"
                rec["source_version"] = meta["commit_sha"]
                rec["tags"] = ["awesome:saadeghi"]
                rec["relationships"] = [{"type": "listed_in", "target": repo_rec["record_id"]}]
                records.append(rec)
    else:  # S07 klaufel: sectioned bullet lists
        for sec in md_sections(readme):
            title = sec["title"].lower()
            if title in ("contents", "contributing") or not sec["body"].strip():
                continue
            for line in sec["body"].splitlines():
                ls = line.strip()
                if not ls.startswith(("- [", "* [")):
                    continue
                m = MD_LINK.search(ls)
                if not m:
                    continue
                name, url = m.group(1), m.group(2)
                desc = ls[m.end():].lstrip(" -–:").strip() or None
                if "known" in title and "companies" in title:
                    rec = system_record(sid, name, name, evidence_url=blob, method="repository", docs_url=url, description=desc)
                else:
                    rec = resource_record(sid, f"{sec['title']}-{url}", name, url, summary=desc, evidence_url=blob,
                                          method="repository", kind=slugify(sec["title"]), category=KLAUFEL_CAT.get(title, "C12"),
                                          status="community")
                rec["source_section"] = " > ".join(sec["path"])
                rec["source_file_path"] = "README.md"
                rec["source_version"] = meta["commit_sha"]
                rec["relationships"] = [{"type": "listed_in", "target": repo_rec["record_id"]}]
                records.append(rec)
    cov["items_found"] = len(records) - 1
    return _done(cov, records)


# ═════════════════════════════ S09 Style Dictionary ═════════════════════════════
SD_DOCS = "docs/src/content/docs/"


def _heading_items(md: str, level: int) -> List[Dict[str, Any]]:
    return [s for s in md_sections(md) if s["level"] == level]


def run_style_dictionary(seed):
    sid = "S09"
    cov = new_coverage(seed)
    cov["extraction_method"] = "GitHub REST API + documentation Markdown at pinned commit + npm registry version"
    cov["provides"] = "original"
    records: List[Dict[str, Any]] = []
    probe_seed(seed, cov)
    full = "amzn/style-dictionary"
    meta, readme = _load_repo(seed, cov, full)
    if meta.get("error"):
        return _done(cov, records)
    sha = meta["commit_sha"]
    pkg = GITHUB.raw(full, sha, "package.json", sid)
    pkg_version = json.loads(pkg).get("version") if pkg else None
    npm_v = npm_latest("style-dictionary", sid)
    cov["version_context"].update({"package_json_version": pkg_version, "npm_latest": npm_v})
    repo_rec = _repo_record(sid, meta, "C03", readme)
    repo_rec["source_version"] = f"{pkg_version} @ {sha[:7]}"
    records.append(repo_rec)

    tool = make_record("tool", sid, "style-dictionary", "Style Dictionary", primary_category="C03",
                       summary=excerpt(meta.get("description"), 400), source_url=seed["url"], extraction_method="repository",
                       source_status="official", license=meta.get("license"), source_version=pkg_version)
    tool["technologies"] = ["JavaScript", "Node.js"]
    tool["platforms"] = ["Web", "iOS", "Android", "Flutter"]

    def doc(path: str) -> Optional[str]:
        cov["pages_attempted"] += 1
        t = GITHUB.raw(full, sha, SD_DOCS + path, sid)
        cov["pages_ok"] += int(bool(t))
        return t

    def sub(kind: str, name: str, body: str, path: str, section: str, category="C03", extra=None):
        r = make_record("tool", sid, f"{kind}-{name}", f"Style Dictionary {kind.replace('_', ' ')}: {name}",
                        summary=excerpt(_strip_md(body), 400), primary_category=category,
                        source_url=GITHUB.blob_url(full, sha, SD_DOCS + path), extraction_method="repository",
                        source_status="official", source_version=pkg_version)
        r["source_file_path"] = SD_DOCS + path
        r["source_section"] = section
        r["repository_url"] = meta.get("html_url")
        r["normalized_content"] = {"kind": f"style_dictionary_{kind}", "name": name, **(extra or {})}
        code = re.findall(r"```(\w*)\n(.*?)```", body, re.S)
        if code:
            r["normalized_content"]["examples"] = [{"lang": l or None, "code": c.strip()[:1500]} for l, c in code[:3]]
        r["relationships"] = [{"type": "part_of", "target": tool["record_id"]}]
        r["confidence"] = "high"
        r["verification_status"] = "verified"
        records.append(r)
        return r

    counts = {}
    t = doc("reference/Hooks/Transforms/predefined.mdx")
    if t:
        items = [s for s in md_sections(t) if s["level"] == 3]
        for s in items:
            ttype = re.search(r"\btype\b[^\n]*?`?(value|name|attribute)`?", s["body"], re.I)
            sub("transform", s["title"].strip("`"), s["body"], "reference/Hooks/Transforms/predefined.mdx", " > ".join(s["path"]),
                extra={"transform_type": ttype.group(1).lower() if ttype else None})
        counts["transforms"] = len(items)
    t = doc("reference/Hooks/Transform Groups/predefined.md")
    if t:
        items = [s for s in md_sections(t) if s["level"] == 3]
        for s in items:
            members = re.findall(r"\[`?([\w/:-]+)`?\]\(", s["body"]) or re.findall(r"`([\w]+/[\w/-]+)`", s["body"])
            sub("transform_group", s["title"].strip("`"), s["body"], "reference/Hooks/Transform Groups/predefined.md", " > ".join(s["path"]),
                extra={"transforms": sorted(set(members))})
        counts["transform_groups"] = len(items)
    t = doc("reference/Hooks/Formats/predefined.md")
    if t:
        items = [s for s in md_sections(t) if s["level"] == 3]
        for s in items:
            sub("format", s["title"].strip("`"), s["body"], "reference/Hooks/Formats/predefined.md", " > ".join(s["path"]))
        counts["formats"] = len(items)
    for path, kind, cat in [("info/architecture.md", "concept", "C09"), ("info/DTCG.mdx", "concept", "C03"),
                            ("reference/config.md", "concept", "C09"), ("reference/Utils/references.md", "concept", "C03"),
                            ("info/tokens.md", "concept", "C03"), ("reference/Hooks/preprocessors.md", "concept", "C09"),
                            ("reference/Hooks/filters.md", "concept", "C09"), ("reference/Hooks/actions.md", "concept", "C09"),
                            ("versions/v4/migration.md", "migration_guide", "C08"), ("versions/v5/migration.md", "migration_guide", "C08")]:
        t = doc(path)
        if not t:
            continue
        for s in md_sections(t):
            if s["level"] in (1, 2) and len(s["body"].strip()) > 80:
                sub(kind, f"{path.split('/')[-1].split('.')[0]} — {s['title']}", s["body"], path, " > ".join(s["path"]), category=cat)
    tool["normalized_content"] = {"kind": "token_build_system", "counts": counts, "npm_latest": npm_v,
                                  "package_json_version": pkg_version, "docs_site": "https://styledictionary.com"}
    tool["confidence"] = "high"
    tool["verification_status"] = "verified"
    records.insert(1, tool)
    cov["items_found"] = len(records)
    cov["coverage_notes"].append(counts)
    cov["limitations"].append("Examples directory READMEs were not decomposed; repository code was not executed.")
    return _done(cov, records)


def _strip_md(s: str) -> str:
    s = re.sub(r"```.*?```", " ", s, flags=re.S)
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"^\s*(import|export) .*$", " ", s, flags=re.M)
    s = MD_LINK.sub(r"\1", s)
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
    return re.sub(r"\s+", " ", s).strip()


# ═════════════════════════════ S10 DTCG ═════════════════════════════
def run_dtcg(seed):
    sid = "S10"
    cov = new_coverage(seed)
    cov["extraction_method"] = "GitHub REST API + technical-report Markdown at pinned commit + published TR page"
    cov["provides"] = "original"
    records: List[Dict[str, Any]] = []
    probe_seed(seed, cov)
    full = "design-tokens/community-group"
    meta, readme = _load_repo(seed, cov, full)
    if meta.get("error"):
        return _done(cov, records)
    sha = meta["commit_sha"]
    repo_rec = _repo_record(sid, meta, "C03", readme)
    records.append(repo_rec)

    # Published technical-report status (maturity) from the public TR site
    status = {}
    for u in ("https://www.designtokens.org/tr/", "https://tr.designtokens.org/format/"):
        r = FETCHER.get(u, source_id=sid, parent=seed["url"], depth=1)
        cov["pages_attempted"] += 1
        if r and r.ok:
            cov["pages_ok"] += 1
            txt = re.sub(r"<[^>]+>", " ", r.text)
            txt = re.sub(r"\s+", " ", txt)
            mats = sorted(set(re.findall(r"(Final Community Group Report|Draft Community Group Report|Community Group Draft Report|Editor['’]s Draft|W3C Community Group[^.]{0,60})", txt)))
            vers = sorted(set(re.findall(r"\b(20\d\d\.\d{1,2})\b", txt)))
            status[u] = {"final_url": r.final_url, "title": page_meta(r.text, r.final_url)["title"], "maturity_mentions": mats[:6], "version_mentions": vers[:10]}
    cov["version_context"]["published_tr"] = status

    folders = {"format": "C03", "color": "C02", "resolver": "C10"}
    for path in sorted(p for p in meta["paths"] if p.startswith("technical-reports/") and p.endswith(".md")):
        folder = path.split("/")[1] if path.count("/") >= 2 else "root"
        t = GITHUB.raw(full, sha, path, sid)
        cov["pages_attempted"] += 1
        if not t:
            continue
        cov["pages_ok"] += 1
        for si, s in enumerate(md_sections(t)):
            body = s["body"].strip()
            if not s["title"] or len(body) < 60:
                continue
            spec = make_record("specification", sid, f"{path}#{si}-{s['title']}", f"DTCG {folder}: {s['title']}", summary=excerpt(_strip_md(body), 500),
                               primary_category=folders.get(folder, "C03"), source_url=GITHUB.blob_url(full, sha, path),
                               extraction_method="repository", source_status="official", source_version=sha)
            spec["source_file_path"] = path
            spec["source_section"] = " > ".join(s["path"])
            spec["repository_url"] = meta.get("html_url")
            normative = re.findall(r"\b(MUST NOT|MUST|SHOULD NOT|SHOULD|MAY|REQUIRED|RECOMMENDED|OPTIONAL)\b", body)
            types_in = sorted(set(re.findall(r'"\$type"\s*:\s*"([\w-]+)"', body)))
            spec["normalized_content"] = {"report": folder, "file": path, "heading_path": s["path"], "normative_keywords": sorted(set(normative)),
                                          "normative_keyword_count": len(normative), "example_types": types_in,
                                          "example_count": body.count("```") // 2}
            spec["confidence"] = "high"
            spec["verification_status"] = "verified"
            spec["notes"].append("Read from the repository's technical-reports source at the pinned commit; may be ahead of the latest published report.")
            records.append(spec)
            # Token type definitions → dedicated records
            if path.endswith(("format/types.md", "format/composite-types.md")) and s["level"] in (2, 3) and types_in:
                tt = make_record("specification", sid, f"token-type-{s['title']}", f"DTCG token type: {s['title']}", summary=excerpt(_strip_md(body), 400),
                                 primary_category="C03", source_url=GITHUB.blob_url(full, sha, path), extraction_method="repository",
                                 source_status="official", source_version=sha)
                tt["normalized_content"] = {"kind": "token_type", "type_name": s["title"], "type_identifiers": types_in,
                                            "composite": "composite" in path, "examples": [c.strip()[:800] for c in re.findall(r"```\w*\n(.*?)```", body, re.S)[:2]]}
                tt["source_file_path"] = path
                tt["source_section"] = " > ".join(s["path"])
                tt["relationships"] = [{"type": "defined_in", "target": spec["record_id"]}]
                tt["confidence"] = "high"
                tt["verification_status"] = "verified"
                records.append(tt)
    cov["items_found"] = len(records)
    cov["limitations"].append("Meeting notes, issues and discussions were not mined. Maturity is reported from the published TR pages as found; repository Markdown may describe unreleased changes.")
    return _done(cov, records)


# ═════════════════════════════ S19 Design System Checklist ═════════════════════════════
def js_object_to_python(src: str) -> Any:
    """Convert a simple `export default {...}` JS object literal (no functions) into Python data."""
    src = re.sub(r"^\s*export\s+default\s+", "", src.strip()).rstrip(";\n ")
    out, i, n = [], 0, len(src)
    while i < n:
        c = src[i]
        if c in "\"'`":
            q, j, buf = c, i + 1, []
            while j < n and src[j] != q:
                if src[j] == "\\" and j + 1 < n:
                    buf.append(src[j:j + 2]); j += 2; continue
                buf.append(src[j]); j += 1
            s = "".join(buf)
            if q != '"':
                s = s.replace('\\' + q, q).replace('"', '\\"')
            out.append('"' + s.replace("\n", "\\n") + '"')
            i = j + 1
        elif src.startswith("//", i):
            i = src.find("\n", i) if src.find("\n", i) != -1 else n
        elif src.startswith("/*", i):
            i = src.find("*/", i) + 2
        elif c.isalpha() or c in "_$":
            j = i
            while j < n and (src[j].isalnum() or src[j] in "_$"):
                j += 1
            word = src[i:j]
            k = j
            while k < n and src[k].isspace():
                k += 1
            if k < n and src[k] == ":" and word not in ("true", "false", "null"):
                out.append(f'"{word}"')
            else:
                out.append(word)
            i = j
        else:
            out.append(c)
            i += 1
    js = "".join(out)
    js = re.sub(r",(\s*[}\]])", r"\1", js)
    return json.loads(js)


def run_checklist(seed):
    sid = "S19"
    cov = new_coverage(seed)
    cov["extraction_method"] = "seed probe; discovered substitute repository via GitHub REST API + raw source files"
    records: List[Dict[str, Any]] = []
    r = probe_seed(seed, cov)
    meta = GITHUB.repo("ardeshireshghi/design-system-checklist", sid)
    cov["pages_attempted"] += 1
    if r is None or not r.ok or meta.get("error"):
        cov["crawl_status"] = f"unavailable (seed HTTP {r.status if r else 'n/a'}; API: {meta.get('error')})"
        cov["errors"].append("Supplied repository does not resolve (404). Recorded as unavailable; not silently dropped.")
    # Discovery: designsystemchecklist.com links its source repository under 'Contribute'
    site = FETCHER.get("https://www.designsystemchecklist.com/", source_id=sid, parent=seed["url"], depth=1)
    cov["pages_attempted"] += 1
    linked = None
    if site and site.ok:
        cov["pages_ok"] += 1
        m = re.search(r'https://github\.com/([\w.-]+/design-system-checklist)', site.text)
        linked = m.group(1) if m else None
    cov["discovered_substitute"] = linked
    if not linked:
        cov["limitations"].append("No substitute repository could be discovered.")
        return _done(cov, records)
    sub_meta = GITHUB.repo(linked, sid)
    cov["pages_attempted"] += 3
    if sub_meta.get("error"):
        cov["errors"].append(f"substitute: {sub_meta['error']}")
        return _done(cov, records)
    cov["pages_ok"] += 3
    sha = sub_meta["commit_sha"]
    cov["version_context"] = {"substitute_repo": linked, "commit_sha": sha, "commit_date": sub_meta.get("commit_date")}
    readme = GITHUB.raw(linked, sha, "README.md", sid)
    repo_rec = _repo_record(sid, sub_meta, "C08", readme)
    repo_rec["notes"].append(f"Discovered substitute for the unavailable seed {seed['url']} (linked as the source repository from designsystemchecklist.com).")
    records.append(repo_rec)
    lic = sub_meta.get("license")
    keep_full = lic in PERMISSIVE
    cats = sorted({p.split("/")[-1][:-3] for p in sub_meta["paths"] if p.startswith("src/translations/en/") and p.endswith(".js") and not p.endswith(("index.js", "core.js"))})
    order_files = {c: GITHUB.raw(linked, sha, f"src/data/{c}.js", sid) for c in cats}
    total = 0
    for cat in cats:
        tpath = f"src/translations/en/{cat}.js"
        txt = GITHUB.raw(linked, sha, tpath, sid)
        cov["pages_attempted"] += 2
        if not txt:
            continue
        cov["pages_ok"] += 1 + int(bool(order_files.get(cat)))
        try:
            tr = js_object_to_python(txt)
            data = js_object_to_python(order_files[cat]) if order_files.get(cat) else {}
        except Exception as e:
            cov["errors"].append(f"{tpath}: parse error {e}")
            continue
        order = {s["id"]: (i, s.get("checklist", []), s.get("resources", [])) for i, s in enumerate(data.get("sections", []))}
        cat_title = tr.get("title", cat)
        for sec_id, sec in tr.get("sections", {}).items():
            si, sorder, sres = order.get(sec_id, (999, [], []))
            for item_id, item in sec.get("checklist", {}).items():
                pos = sorder.index(item_id) if item_id in sorder else None
                desc = item.get("description", "")
                g = make_record("guideline", sid, item_id, f"{cat_title} › {sec.get('title')} › {item.get('title')}",
                                summary=desc if keep_full else excerpt(desc, 160), primary_category=_checklist_cat(cat, sec.get("title", "")),
                                source_url=GITHUB.blob_url(linked, sha, tpath), extraction_method="repository", source_status="community")
                g["source_file_path"] = tpath
                g["source_section"] = f"{cat_title} > {sec.get('title')}"
                g["source_version"] = sha
                g["license"] = lic
                g["normalized_content"] = {
                    "kind": "checklist_item", "checklist_id": item_id, "requirement": item.get("title"), "category": cat_title,
                    "section": sec.get("title"), "section_id": sec_id, "section_description": sec.get("description") if keep_full else excerpt(sec.get("description"), 160),
                    "rationale": None, "verification_method": None, "priority": None, "order": {"section": si, "item": pos},
                    "source_wording": desc if keep_full else None, "section_resources": sres,
                }
                g["evidence_excerpt"] = excerpt(desc, 300)
                g["confidence"] = "high"
                g["verification_status"] = "verified"
                g["notes"].append("Priority not stated by source; left null.")
                g["relationships"] = [{"type": "part_of", "target": repo_rec["record_id"]}]
                records.append(g)
                total += 1
    cov["items_found"] = total
    cov["crawl_status"] = "unavailable_seed__substitute_extracted"
    cov["limitations"].append(f"Seed repository 404. Items were extracted from the discovered repository {linked} (English translation files), which is the source linked by designsystemchecklist.com.")
    return _done(cov, records)


def _checklist_cat(cat: str, section: str) -> str:
    s = section.lower()
    if cat == "maintenance":
        return "C08"
    if cat == "components":
        return "C05"
    if cat == "designLanguage":
        return "C07" if "access" in s else "C01"
    return "C02"
