"""Adapters for directory / gallery / publication sources: S01–S05, S17, S18, S20."""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

from bs4 import NavigableString, Tag

from ..core import FETCHER, canonical_url, excerpt, make_record, sha256, slugify
from .common import (abs_links, fetch_many, new_coverage, page_meta, probe_seed, resource_record, soup_of,
                     system_record, visible_text)


def _done(cov: Dict[str, Any], records: List[Dict[str, Any]]) -> Dict[str, Any]:
    cov["records_emitted"] = len(records)
    return {"records": records, "coverage": cov}


# ═════════════════════════════ S01 Design Systems Surf ═════════════════════════════
NOISE = {"View source", "$", "Source", "Figma", "Repository"}


def _surf_walk(html: str):
    """Yield (section, card_texts, anchor_text, href) in document order for external anchors.
    card_texts are the strings of the anchor's nearest ancestor that carries any non-noise text
    (Framer emits hidden '$' nodes, so preceding-text heuristics are unreliable)."""
    s = soup_of(html)
    for t in s(["script", "style", "svg", "noscript"]):
        t.decompose()
    section = None
    for el in (s.body or s).descendants:
        if isinstance(el, Tag) and el.name in ("h1", "h2"):
            section = el.get_text(" ", strip=True)
        elif isinstance(el, Tag) and el.name == "a" and el.get("href", "").startswith("http"):
            texts, p = [], el
            for _ in range(5):
                p = p.parent
                if p is None:
                    break
                texts = [t for t in p.stripped_strings if t not in NOISE]
                if texts:
                    break
            yield section, texts, el.get_text(" ", strip=True), el["href"]


def run_surf(seed):
    cov = new_coverage(seed)
    cov["extraction_method"] = "html (server-rendered Framer pages) + sitemap.xml"
    cov["provides"] = "mixed"
    records: List[Dict[str, Any]] = []
    probe_seed(seed, cov)
    sm = FETCHER.get("https://designsystems.surf/sitemap.xml", source_id="S01", parent=seed["url"], depth=1)
    if not sm or not sm.ok:
        cov["errors"].append("sitemap unavailable")
        return _done(cov, records)
    locs = re.findall(r"<loc>(.*?)</loc>", sm.text)
    groups: Dict[str, List[str]] = {}
    for u in locs:
        parts = urlparse(u).path.strip("/").split("/")
        if len(parts) == 2:
            groups.setdefault(parts[0], []).append(u)
    cov["coverage_notes"].append({k: len(v) for k, v in groups.items()})

    # Design-system detail pages ------------------------------------------------
    ds_pages = fetch_many([(u, sm.final_url, 1) for u in groups.get("design-systems", [])], "S01", cov)
    for url, r in ds_pages.items():
        if not r or not r.ok:
            continue
        text = visible_text(r.text)
        toks = [t for t in text.split("\n") if t]
        s = soup_of(r.text)
        h1 = s.find("h1")
        org = h1.get_text(" ", strip=True) if h1 else None
        name, fc, cc, desc = None, None, None, []
        try:
            i = next(k for k in range(len(toks) - 1) if toks[k] == "from" and toks[k + 1] == org)
            name = toks[i - 1]
            m = re.search(r"Foundations:\s*\n?(\d+)\s*\n?/\s*\n?Components:\s*\n?(\d+)", text)
            if m:
                fc, cc = int(m.group(1)), int(m.group(2))
            j = toks.index("Components:", i) + 2 if "Components:" in toks[i:] else i + 2
            while j < len(toks) and toks[j] not in ("Source", "Figma", "Repository", "featured resource"):
                desc.append(toks[j])
                j += 1
        except StopIteration:
            name = org
        top: Dict[str, str] = {}
        foundations, components, seen = [], [], set()
        for section, prev, atext, href in _surf_walk(r.text):
            if atext in ("Source", "Figma", "Repository") and section == org:
                top.setdefault(atext, href)
            elif atext == "View source" and prev:
                item = prev[0]
                key = (section, item, href)
                if key in seen:
                    continue
                seen.add(key)
                (foundations if section == "Foundations" else components if section == "Components" else []).append({"name": item, "url": href})
        slug = urlparse(url).path.rsplit("/", 1)[-1]
        rec = system_record("S01", slug, name or slug, organization=org, evidence_url=url, docs_url=top.get("Source"),
                            repo_url=top.get("Repository"), figma_url=top.get("Figma"), description=" ".join(desc) or None,
                            attributes={"foundations_count_claimed": fc, "components_count_claimed": cc,
                                        "foundations": foundations, "components": components})
        rec["evidence_excerpt"] = excerpt(" ".join(desc), 300)
        rec["tags"] = ["directory:surf"]
        records.append(rec)
        # One component-index record per (system, component) link — evidence that the system documents it.
        for c in components:
            cr = make_record("component", "S01", f"{slug}-{c['name']}-{sha256(c['url'].encode())[:8]}", c["name"], summary=None, primary_category="C05",
                             source_url=url, extraction_method="html", source_status="third_party")
            cr.update(organization=org, design_system=name)
            cr["normalized_content"] = {"component_name": c["name"], "library": name, "organization": org,
                                        "documentation_url": c["url"], "detail_level": "index"}
            cr["relationships"] = [{"type": "documented_by_system", "target": rec["record_id"]}]
            cr["notes"].append("Index-level record from Design Systems Surf; the linked official page was not inspected.")
            records.append(cr)
        for f in foundations:
            gr = make_record("guideline", "S01", f"{slug}-foundation-{f['name']}-{sha256(f['url'].encode())[:8]}", f"{name}: {f['name']}", primary_category="C02",
                             source_url=url, extraction_method="html", source_status="third_party")
            gr.update(organization=org, design_system=name)
            gr["normalized_content"] = {"kind": "foundation_doc_link", "topic": f["name"], "documentation_url": f["url"], "detail_level": "index"}
            gr["relationships"] = [{"type": "foundation_of", "target": rec["record_id"]}]
            records.append(gr)

    # Component overview pages ---------------------------------------------------
    cp = fetch_many([(u, sm.final_url, 1) for u in groups.get("components", [])], "S01", cov)
    for url, r in cp.items():
        if not r or not r.ok:
            continue
        s = soup_of(r.text)
        h1 = s.find("h1")
        cname = h1.get_text(" ", strip=True) if h1 else urlparse(url).path.rsplit("/", 1)[-1]
        toks = [t for t in visible_text(r.text).split("\n") if t]
        desc = []
        try:
            k = len(toks) - 1 - toks[::-1].index(cname)  # last occurrence = page title
            for t in toks[k + 1:]:
                if t == "featured resource":
                    break
                desc.append(t)
        except ValueError:
            pass
        examples, seen = [], set()
        for section, prev, atext, href in _surf_walk(r.text):
            if atext == "View source" and len(prev) >= 2 and href not in seen:
                seen.add(href)
                examples.append({"organization": prev[0], "system": prev[1], "url": href})
        rec = make_record("pattern", "S01", f"component-overview-{cname}", f"Component overview: {cname}",
                          summary=excerpt(" ".join(desc), 600), primary_category="C05", source_url=url,
                          extraction_method="html", source_status="third_party")
        rec["normalized_content"] = {"kind": "cross_system_component_overview", "component_name": cname,
                                     "description": " ".join(desc) or None, "implementations": examples}
        rec["evidence_excerpt"] = excerpt(" ".join(desc), 300)
        records.append(rec)
        cov["items_found"] += 1

    # Directories listed by Surf -------------------------------------------------
    dp = fetch_many([(u, sm.final_url, 1) for u in groups.get("directories", [])], "S01", cov)
    for url, r in dp.items():
        if not r or not r.ok:
            continue
        meta = page_meta(r.text, url)
        ext = [h for (h, t) in abs_links(r.text, url) if "designsystems.surf" not in h and t in ("Visit", "View source", "Source", "Visit website", "Website")]
        title = (meta["title"] or url).split("|")[0].strip()
        records.append(resource_record("S01", f"directory-{urlparse(url).path}", title, ext[0] if ext else url, summary=meta["description"],
                                       evidence_url=url, kind="directory"))
    for kind in ("articles", "guides", "products", "blueprints"):
        for u in groups.get(kind, []):
            t = urlparse(u).path.rsplit("/", 1)[-1].replace("-", " ").title()
            rr = resource_record("S01", f"{kind}-{u}", t, u, evidence_url=sm.final_url, kind=kind[:-1], method="sitemap",
                                 status="third_party")
            rr["notes"].append("Discovered via sitemap only; page not fetched (title derived from URL slug).")
            rr["confidence"] = "low"
            records.append(rr)
    cov["items_found"] += len(ds_pages)
    cov["limitations"].append("Surf 'Pro' content and signed-in features were not accessed. Component-to-system links are index-level; linked official pages were not inspected by this adapter.")
    return _done(cov, records)


# ═════════════════════════════ S02 Adele ═════════════════════════════
def run_adele(seed):
    cov = new_coverage(seed)
    cov["extraction_method"] = "html table (server-rendered)"
    cov["provides"] = "original"
    records: List[Dict[str, Any]] = []
    r = probe_seed(seed, cov)
    if not r or not r.ok:
        return _done(cov, records)
    s = soup_of(r.text)
    rows = s.find_all("tr")
    header = [th.get_text(" ", strip=True).replace(" A/Z", "") for th in rows[0].find_all(["th", "td"])]
    data_rows = rows[2:]  # row 1 holds filter controls
    for tr in data_rows:
        tds = tr.find_all("td")
        if len(tds) == len(header) + 1:
            tds = tds[1:]  # leading logo cell
        cells = {}
        links = {}
        for h, td in zip(header, tds):
            cells[h] = td.get_text(" ", strip=True)
            hrefs = [urljoin(r.final_url, a["href"]) for a in td.find_all("a", href=True)]
            if hrefs:
                links[h] = hrefs
        company, system = cells.get("Company"), cells.get("System", "")
        if not company or company == "Placeholder":
            continue
        deprecated = system.endswith("Deprecated")
        sysname = system.replace("Deprecated", "").strip()
        detail = (links.get("Company") or [None])[0]
        repo = next((h for h in links.get("repository", []) if "github" in h or "gitlab" in h or "bitbucket" in h), None)
        storybook = (links.get("storybook") or [None])[0]
        attrs = {k: v for k, v in cells.items() if k not in ("Company", "System") and v}
        rec = system_record("S02", f"{company}-{sysname}", sysname, organization=company, evidence_url=r.final_url,
                            docs_url=(links.get("System") or [None])[0], repo_url=repo,
                            storybook_url=storybook if storybook and storybook.startswith("http") else None,
                            attributes={**attrs, "adele_detail_url": detail, "deprecated_label": deprecated, "cell_links": links},
                            frameworks=[f.strip() for f in re.split(r"[,/]", cells.get("JS library/framework", "")) if f.strip() and f.strip().lower() not in ("no data", "no")])
        rec["source_section"] = "Main comparison table"
        rec["tags"] = ["directory:adele"] + (["deprecated"] if deprecated else [])
        rec["evidence_excerpt"] = excerpt(" | ".join(f"{k}: {v}" for k, v in list(attrs.items())[:8]), 300)
        records.append(rec)
    cov["items_found"] = len(records)
    cov["coverage_notes"].append({"table_columns": header, "rows": len(records)})
    cov["limitations"].append("Per-system Adele detail pages were not crawled; the main table carries the same attribute set. Values are Adele's own audit claims and dates are not shown per cell.")
    return _done(cov, records)


# ═════════════════════════════ S03 Design Systems Repo ═════════════════════════════
def run_dsrepo(seed):
    cov = new_coverage(seed)
    cov["extraction_method"] = "html (static site)"
    cov["provides"] = "links"
    records: List[Dict[str, Any]] = []
    probe_seed(seed, cov)
    pages = {"design-systems": "system", "articles": "article", "tools": "tool", "books": "book", "talks": "talk"}
    res = fetch_many([(f"https://designsystemsrepo.com/{p}/", seed["url"], 1) for p in pages], "S03", cov)
    for path, kind in pages.items():
        r = res.get(f"https://designsystemsrepo.com/{path}/")
        if not r or not r.ok:
            continue
        s = soup_of(r.text)
        blocks = s.select("a.block") or []
        seen_keys = set()
        for b in blocks:
            href = b.get("href")
            if (kind, href) in seen_keys:
                continue
            seen_keys.add((kind, href))
            parts = [t for t in b.stripped_strings]
            if not href or not parts:
                continue
            if kind == "system":
                org = parts[0] if len(parts) >= 3 else None
                name = parts[1] if len(parts) >= 3 else parts[0]
                desc = " ".join(parts[2:]) if len(parts) >= 3 else " ".join(parts[1:])
                rec = system_record("S03", f"{org}-{name}", name, organization=org, evidence_url=r.final_url, docs_url=href, description=desc)
                rec["tags"] = ["directory:dsrepo"]
                records.append(rec)
            else:
                title = parts[0]
                rr = resource_record("S03", f"{kind}-{href}", title, href, summary=" ".join(parts[1:]) or None, evidence_url=r.final_url,
                                     kind=kind, category="C08" if kind in ("article", "talk", "book") else "C09")
                records.append(rr)
        cov["coverage_notes"].append({path: len(blocks)})
    cov["items_found"] = len(records)
    if not records:
        cov["limitations"].append("No card blocks matched selector 'a.block'; layout may have changed.")
    return _done(cov, records)


# ═════════════════════════════ S04 Storybook Showcase ═════════════════════════════
def _next_data(html: str) -> Optional[Dict[str, Any]]:
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    return json.loads(m.group(1)) if m else None


def run_storybook(seed):
    cov = new_coverage(seed)
    cov["extraction_method"] = "Next.js __NEXT_DATA__ embedded JSON (catalog + project detail pages)"
    cov["provides"] = "original"
    records: List[Dict[str, Any]] = []
    r = probe_seed(seed, cov)
    if not r or not r.ok:
        return _done(cov, records)
    nd = _next_data(r.text) or {}
    pp = nd.get("props", {}).get("pageProps", {})
    projects = pp.get("projects", [])
    cov["coverage_notes"].append({"catalog_projects_in_page_data": len(projects), "numShowingIncrement": pp.get("numShowingIncrement")})
    details = fetch_many([(f"https://storybook.js.org/showcase/{p['slug']}", r.final_url, 1) for p in projects], "S04", cov)
    for p in projects:
        url = f"https://storybook.js.org/showcase/{p['slug']}"
        d = details.get(url)
        dp = (_next_data(d.text) or {}).get("props", {}).get("pageProps", {}) if d and d.ok else {}
        rec = system_record("S04", p["slug"], p.get("title") or p["slug"], organization=p.get("org"), evidence_url=url,
                            docs_url=None, repo_url=dp.get("gitHubUrl"), storybook_url=dp.get("storybookUrl"),
                            description=dp.get("description"),
                            attributes={"component_count": dp.get("componentCount", p.get("componentCount")),
                                        "addons": [a.get("name") if isinstance(a, dict) else a for a in dp.get("addons", [])],
                                        "tags": [t.get("name") if isinstance(t, dict) else t for t in dp.get("tags", [])],
                                        "package_name": dp.get("packageName"), "package_downloads": dp.get("packageDownloads"),
                                        "showcase_score": p.get("score"), "updated_at": dp.get("updatedAt")})
        rec["tags"] = ["showcase:storybook"]
        rec["source_status"] = "third_party"
        rec["verification_status"] = "partially_verified" if dp.get("storybookUrl") else "unverified"
        rec["notes"] = ["Storybook URL and metadata as published on the Storybook Showcase; the linked Storybook was not crawled."]
        records.append(rec)
    cov["items_found"] = len(projects)
    cov["limitations"].append(f"Catalog enumerated from the showcase page data ({len(projects)} projects). Individual Storybook instances (stories, props, variants) were not crawled; doing so requires per-instance inspection.")
    return _done(cov, records)


# ═════════════════════════════ S05 Design Systems Directory ═════════════════════════════
def run_dsdir(seed):
    cov = new_coverage(seed)
    cov["extraction_method"] = "html inspection"
    cov["provides"] = "links"
    r = probe_seed(seed, cov)
    records: List[Dict[str, Any]] = []
    if r and r.ok:
        uses_cse = "cse.google.com" in r.text
        m = re.search(r"Search over (\d+) design systems", r.text)
        rec = resource_record("S05", "designsystems-directory", "Design Systems Directory", seed["url"],
                              summary=page_meta(r.text, r.final_url)["description"], evidence_url=r.final_url, kind="directory")
        rec["normalized_content"].update({"claimed_system_count": int(m.group(1)) if m else None, "search_backend": "Google Programmable Search Engine" if uses_cse else None})
        records.append(rec)
        if uses_cse:
            cov["crawl_status"] = "inspected_partial"
            cov["limitations"].append("The site is a Google Programmable Search Engine front-end; its indexed catalogue is not exposed as enumerable pages or data. Results were not scraped (querying Google's CSE programmatically is out of scope). Only site metadata and the claimed count were recorded.")
    cov["items_found"] = len(records)
    return _done(cov, records)


# ═════════════════════════════ S17 The Design System Guide ═════════════════════════════
def run_dsguide(seed):
    cov = new_coverage(seed)
    cov["extraction_method"] = "html (heading-scoped link extraction)"
    cov["provides"] = "links"
    records: List[Dict[str, Any]] = []
    r = probe_seed(seed, cov)
    if not r or not r.ok:
        return _done(cov, records)
    s = soup_of(r.text)
    for t in s(["script", "style", "svg", "nav", "footer"]):
        t.decompose()
    section, seen = None, set()
    root = s.find("main") or s.body
    for el in root.descendants:
        if isinstance(el, Tag) and el.name in ("h1", "h2", "h3"):
            section = el.get_text(" ", strip=True)
        elif isinstance(el, Tag) and el.name == "a" and el.get("href"):
            href = urljoin(r.final_url, el["href"])
            text = el.get_text(" ", strip=True)
            if not text or "thedesignsystem.guide" in href and not href.rstrip("/").endswith(("course", "airbundle")):
                continue
            key = (section, href)
            if key in seen or not section:
                continue
            seen.add(key)
            # description: nearest following text within the same card
            card = el.find_parent(["div", "li"])
            desc = None
            if card:
                txt = card.get_text(" ", strip=True)
                desc = txt.replace(text, "", 1).strip() or None
            cat = "C07" if "access" in section.lower() else "C02" if "color" in section.lower() else "C13" if section.lower().startswith("ai") else "C09"
            rr = resource_record("S17", f"{section}-{href}", text[:160], href, summary=desc, evidence_url=r.final_url,
                                 kind=slugify(section), category=cat)
            rr["source_section"] = section
            records.append(rr)
    cov["items_found"] = len(records)
    cov["limitations"].append("Descriptions are taken from the card text around each link; some source entries have no URL or a mismatched URL (recorded as published).")
    return _done(cov, records)


# ═════════════════════════════ S18 DesignSystems.com ═════════════════════════════
def run_dscom(seed):
    cov = new_coverage(seed)
    cov["extraction_method"] = "html (home + section index pages + article meta)"
    cov["provides"] = "original"
    records: List[Dict[str, Any]] = []
    r = probe_seed(seed, cov)
    if not r or not r.ok:
        return _done(cov, records)
    links = abs_links(r.text, r.final_url)
    sections = sorted({canonical_url(h) for h, _ in links if "/sections/" in h})
    sec_pages = fetch_many([(u, r.final_url, 1) for u in sections], "S18", cov)
    article_urls = set()
    for h, t in links + [l for sp in sec_pages.values() if sp and sp.ok for l in abs_links(sp.text, sp.final_url)]:
        cu = canonical_url(h)
        if host_ok(cu) and cu.count("/") == 3 and not any(x in cu for x in ("/sections", "/tag", "/author", "/page")) and cu != canonical_url(r.final_url):
            article_urls.add(cu)
        if "figma.com/community/file" in h:
            rr = resource_record("S18", f"figma-{h}", t or h, h, evidence_url=r.final_url, kind="figma_community_file", category="C09")
            records.append(rr)
    arts = fetch_many([(u, r.final_url, 2) for u in sorted(article_urls)][:80], "S18", cov)
    for u, ar in arts.items():
        if not ar or not ar.ok:
            continue
        meta = page_meta(ar.text, u)
        body = visible_text(ar.text)
        title = (meta["title"] or u).split("|")[0].replace("– Design Systems", "").strip()
        low = (title + " " + (meta["description"] or "")).lower()
        cat = ("C07" if "access" in low else "C03" if "token" in low else "C02" if any(k in low for k in ("typograph", "color", "icon", "grid", "space", "layout")) else
               "C08" if any(k in low for k in ("contribut", "govern", "structure", "team", "process", "myth", "adoption")) else "C01")
        rr = resource_record("S18", u, title, u, summary=meta["description"], evidence_url=u, kind="article", category=cat, status="official")
        rr["normalized_content"]["word_count"] = len(body.split())
        rr["evidence_excerpt"] = excerpt(meta["description"] or body, 300)
        records.append(rr)
    cov["items_found"] = len(records)
    cov["coverage_notes"].append({"section_pages": len(sections), "article_candidates": len(article_urls)})
    cov["limitations"].append("Article bodies were fetched to verify title/description; full guidance text was not decomposed into individual guideline records (copyrighted editorial content summarised by metadata only).")
    return _done(cov, records)


def host_ok(u: Optional[str]) -> bool:
    return bool(u) and urlparse(u).netloc in ("designsystems.com", "www.designsystems.com")


# ═════════════════════════════ S20 Design Systems One ═════════════════════════════
def run_dsone(seed):
    cov = new_coverage(seed)
    cov["extraction_method"] = "html gallery + documented public JSON API (advertised in llms.txt)"
    cov["provides"] = "original"
    records: List[Dict[str, Any]] = []
    r = probe_seed(seed, cov)
    # Gallery (all 120): card links
    gallery = []
    if r and r.ok:
        s = soup_of(r.text)
        for a in s.find_all("a", href=True):
            h = urljoin(r.final_url, a["href"])
            if re.match(r"https://www\.designsystems\.one/design-systems/[\w-]+$", h):
                gallery.append((h, [t for t in a.stripped_strings]))
    seen = {}
    for h, parts in gallery:
        seen.setdefault(h, parts)
    api = FETCHER.get("https://www.designsystems.one/api/design-systems", source_id="S20", parent=seed["url"], depth=1)
    rich = {i["slug"]: i for i in (api.json().get("items", []) if api and api.ok else [])}
    ai = FETCHER.get("https://www.designsystems.one/api/ai-ready/systems", source_id="S20", parent=seed["url"], depth=1)
    ai_data = ai.json() if ai and ai.ok else {}
    ai_items = {i["slug"]: i for i in ai_data.get("items", [])}
    cov["pages_attempted"] += 2
    cov["pages_ok"] += int(bool(api and api.ok)) + int(bool(ai and ai.ok))
    details = fetch_many([(f"https://www.designsystems.one/api/design-systems/{slug}", seed["url"], 2) for slug in rich], "S20", cov)
    slugs = set(rich) | {h.rsplit("/", 1)[-1] for h in seen}
    for slug in sorted(slugs):
        page = f"https://www.designsystems.one/design-systems/{slug}"
        base = rich.get(slug, {})
        det_r = details.get(f"https://www.designsystems.one/api/design-systems/{slug}")
        det = det_r.json() if det_r and det_r.ok else {}
        parts = seen.get(page, [])
        name = base.get("name") or det.get("name") or (parts[0] if parts else slug)
        org = base.get("company") or det.get("company") or (parts[1] if len(parts) > 1 else None)
        ext = det.get("externalLinks") or []
        repo_link = next((l["href"] for l in ext if isinstance(l, dict) and re.search(r"github\.com|gitlab\.com", l.get("href", ""))), None)
        rec = system_record("S20", slug, name, organization=org, evidence_url=page, method="api" if det else "html",
                            docs_url=base.get("url") or det.get("url"),
                            repo_url=repo_link,
                            description=base.get("tagline") or det.get("tagline") or (" ".join(parts[2:]) if len(parts) > 2 else None),
                            attributes={"gallery_card_text": parts, "rich_breakdown": bool(det), "breakdown": det or None,
                                        "ai_ready": ai_items.get(slug)})
        rec["tags"] = ["directory:designsystems.one"] + (["ai-ready-index"] if slug in ai_items else [])
        if det:
            rec["evidence_excerpt"] = excerpt(json.dumps({k: det[k] for k in list(det)[:6]}, ensure_ascii=False), 300)
        records.append(rec)
        # Token snapshot → token records (source-native names/values preserved)
        snap = det.get("tokenSnapshot") or det.get("tokens") or None
        for tok in _iter_tokens(snap):
            tr = make_record("token", "S20", f"{slug}-{tok['path']}", tok["path"], primary_category="C03", source_url=page,
                             extraction_method="api", source_status="third_party")
            tr.update(organization=org, design_system=name)
            tr["normalized_content"] = {"token_name": tok["path"].split(".")[-1], "token_path": tok["path"], "raw_value": tok["value"],
                                        "token_type": tok.get("type"), "theme": None, "platform": None, "description": tok.get("description"),
                                        "source_format": "designsystems.one token snapshot"}
            tr["relationships"] = [{"type": "token_of", "target": rec["record_id"]}]
            tr["notes"].append("Snapshot published by DesignSystems.one, not read from the system's own token files.")
            records.append(tr)
        for c in det.get("components", []) or []:
            cr = make_record("component", "S20", f"{slug}-{c.get('name')}", c.get("name") or "?", summary=c.get("note"),
                             primary_category="C05", source_url=page, extraction_method="api", source_status="third_party")
            cr.update(organization=org, design_system=name)
            cr["normalized_content"] = {"component_name": c.get("name"), "library": name, "organization": org,
                                        "description": c.get("note"), "detail_level": "editorial_highlight"}
            cr["relationships"] = [{"type": "documented_by_system", "target": rec["record_id"]}]
            records.append(cr)
        if det.get("governance"):
            gr = make_record("guideline", "S20", f"{slug}-governance", f"{name}: governance (editorial breakdown)", summary=det["governance"],
                             primary_category="C08", source_url=page, extraction_method="api", source_status="third_party")
            gr.update(organization=org, design_system=name)
            gr["normalized_content"] = {"kind": "governance_description", "text": det["governance"], "origin": det.get("origin"),
                                        "known_for": det.get("knownFor"), "watch_outs": det.get("watchOutsFor"),
                                        "evaluation_guidance": det.get("evaluationGuidance")}
            gr["notes"].append("Third-party editorial assessment by DesignSystems.one.")
            records.append(gr)
    # AI-ready signals as guideline/evidence records
    for slug, it in ai_items.items():
        for sig in (it.get("evidence") or {}).get("signals", []):
            gr = make_record("guideline", "S20", f"ai-ready-{slug}-{sig['key']}", f"{it['name']}: {sig['label']} = {sig['status']}",
                             summary=sig.get("note"), primary_category="C13", source_url=ai_data.get("indexUrl") or seed["url"],
                             extraction_method="api", source_status="third_party")
            gr.update(organization=it.get("company"), design_system=it.get("name"))
            gr["normalized_content"] = {"kind": "ai_readiness_signal", **sig}
            gr["license"] = ai_data.get("license")
            gr["confidence"] = "medium" if sig.get("source") else "low"
            records.append(gr)
    cov["items_found"] = len(slugs)
    cov["version_context"] = {"ai_index_audited_at": ai_data.get("auditedAt"), "ai_index_license": ai_data.get("license")}
    cov["coverage_notes"].append({"gallery_cards": len(seen), "rich_breakdowns": len(rich), "ai_ready_systems": len(ai_items)})
    return _done(cov, records)


def _iter_tokens(snap, prefix=""):
    if not snap:
        return
    if isinstance(snap, list):
        for t in snap:
            if isinstance(t, dict) and ("name" in t or "path" in t):
                yield {"path": t.get("path") or t.get("name"), "value": t.get("value") or t.get("$value"), "type": t.get("type") or t.get("$type"), "description": t.get("description") or t.get("role")}
        return
    if isinstance(snap, dict):
        if "$value" in snap or "value" in snap and not isinstance(snap.get("value"), dict):
            yield {"path": prefix.strip("."), "value": snap.get("$value", snap.get("value")), "type": snap.get("$type") or snap.get("type"), "description": snap.get("$description") or snap.get("description")}
            return
        for k, v in snap.items():
            if isinstance(v, (dict, list)):
                yield from _iter_tokens(v, f"{prefix}.{k}")
            elif isinstance(v, (str, int, float)):
                yield {"path": f"{prefix}.{k}".strip("."), "value": v, "type": None, "description": None}
