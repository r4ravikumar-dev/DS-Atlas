"""Official-documentation adapter: verifies a canonical design system against its own documentation.

Discovery order (all same-host, robots-respecting): llms.txt → sitemap.xml → breadth-first links from the root.
URLs are prioritized by documentation value (components, foundations, tokens, theming, accessibility, governance,
installation). Each page yields a resource record; component index pages yield component records; and rule-based
detectors emit *field-level* attribute evidence (attribute path, value, URL, section, short excerpt).

Only explicit statements become `verified`; inferences (e.g. framework from a package name) are `partially_verified`.
Absence of a statement is never recorded as a negative fact."""
from __future__ import annotations

import re
from collections import deque
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from ..core import FETCHER, GITHUB, canonical_url, excerpt, make_record, slugify
from .common import new_coverage, probe_seed, resource_record

TOPICS: List[Tuple[str, str, int]] = [  # (topic, url/title regex, priority weight)
    ("components", r"\bcomponents?\b", 9), ("tokens", r"\btokens?\b", 9), ("theming", r"\btheme|theming|dark[- ]?mode|color[- ]?modes?\b", 8),
    ("accessibility", r"\baccessib|a11y|wcag\b", 8), ("color", r"\bcolou?rs?\b", 7), ("typography", r"\btypograph|\btype\b|fonts?\b", 7),
    ("spacing", r"\bspacing|space\b", 7), ("layout", r"\blayout|grid\b", 6), ("motion", r"\bmotion|animation\b", 5), ("iconography", r"\bicons?|iconograph", 5),
    ("elevation", r"\belevation|shadows?\b", 5), ("radius", r"\bradius|shape|corner", 4), ("installation", r"install|getting[- ]?started|get[- ]?started|develop|setup|quick[- ]?start", 8),
    ("contribution", r"contribut", 7), ("governance", r"governance|principles?|support|roadmap", 5), ("releases", r"release|changelog|versioning|what'?s[- ]new", 7),
    ("migration", r"migrat|upgrade", 5), ("deprecation", r"deprecat", 4), ("browser_support", r"browser[- ]?support|browsers", 5), ("license", r"licen[cs]e", 3),
    ("patterns", r"\bpatterns?\b", 5), ("foundations", r"foundation|guidelines?|styles?\b", 4),
]
FOUNDATION_TOPICS = {"color", "typography", "spacing", "layout", "motion", "iconography", "elevation", "radius"}
FRAMEWORK_WORDS = {"React": r"\breact\b(?!\s*native)", "React Native": r"react[- ]native", "Vue": r"\bvue(?:\.js)?\b", "Angular": r"\bangular\b",
                   "Svelte": r"\bsvelte\b", "Web Components": r"web[- ]components?|custom elements", "iOS": r"\bios\b|swiftui|\bswift\b", "Android": r"\bandroid\b|jetpack compose",
                   "Flutter": r"\bflutter\b", "Ember": r"\bember(?:\.js)?\b"}
PKG_FRAMEWORK = [(r"react[-/]native|/native\b", "React Native"), (r"\breact\b", "React"), (r"\bvue\b", "Vue"), (r"\bangular\b|/ng\b", "Angular"),
                 (r"\bsvelte\b", "Svelte"), (r"web-?components|/wc\b|/elements\b", "Web Components")]
SKIP_EXT = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".pdf", ".zip", ".mp4", ".css", ".js", ".ico", ".woff", ".woff2", ".json", ".xml", ".txt")


def topics_of(url: str, title: str = "") -> List[str]:
    hay = (urlparse(url).path.replace("-", " ").replace("_", " ") + " " + (title or "")).lower()
    return [t for t, rx, _ in TOPICS if re.search(rx, hay)]


def score(url: str, title: str = "", depth: int = 0) -> float:
    s = sum(w for t, rx, w in TOPICS if t in topics_of(url, title))
    return s - depth * 0.5 - len(urlparse(url).path.split("/")) * 0.1


def sentence_with(text: str, rx: str, n: int = 280) -> Optional[str]:
    m = re.search(rx, text, re.I)
    if not m:
        return None
    start = max(0, text.rfind(".", 0, m.start()) + 1, m.start() - n // 2)
    end = text.find(".", m.end())
    end = min(len(text), (end + 1) if end != -1 else m.end() + n // 2, start + n)
    return re.sub(r"\s+", " ", text[start:end]).strip()


def _same_site(u: str, host: str) -> bool:
    h = urlparse(u).netloc.lower()
    return h == host or h.removeprefix("www.") == host.removeprefix("www.")


def parse_page(html: str, url: str) -> Dict[str, Any]:
    s = BeautifulSoup(html[:3_000_000], "lxml")
    for t in s(["script", "style", "noscript", "svg", "template"]):
        t.decompose()
    title = s.title.get_text(" ", strip=True) if s.title else ""
    can = s.find("link", rel="canonical")
    main = s.find("main") or s.find("article") or s.body or s
    text = main.get_text("\n", strip=True)
    heads = [(h.name, h.get_text(" ", strip=True)) for h in main.find_all(["h1", "h2", "h3"])][:80]
    links = [(urljoin(url, a["href"]).split("#")[0], a.get_text(" ", strip=True)) for a in s.find_all("a", href=True)
             if not a["href"].startswith(("mailto:", "javascript:", "tel:"))]
    code = [c.get_text(" ", strip=True) for c in s.find_all(["code", "pre"])][:200]
    desc = s.find("meta", attrs={"name": "description"})
    return {"title": title, "canonical": urljoin(url, can["href"]) if can and can.get("href") else None, "text": text, "headings": heads,
            "links": links, "code": code, "description": desc.get("content") if desc else None}


def run_official_docs(seed: Dict[str, Any]) -> Dict[str, Any]:
    sid = seed["source_id"]
    sys_key, sys_name, org = seed["system_key"], seed.get("system_name"), seed.get("organization")
    max_pages, max_depth = int(seed.get("max_pages") or 45), int(seed.get("max_depth") or 3)
    cov = new_coverage(seed)
    cov["extraction_method"] = f"official documentation crawl (llms.txt → sitemap → links; same host; ≤{max_pages} pages, depth ≤{max_depth})"
    cov["provides"] = "original"
    records: List[Dict[str, Any]] = []
    attrs: List[Dict[str, Any]] = []
    root = probe_seed(seed, cov)
    if not root or not root.ok:
        cov["records_emitted"] = 0
        return {"records": records, "coverage": cov, "attributes": attrs}
    host = urlparse(root.final_url).netloc.lower()
    base = f"{urlparse(root.final_url).scheme}://{host}"

    def attr(path: str, value: Any, url: str, section: Optional[str], ex: Optional[str], status: str = "verified", method: str = "official_docs"):
        attrs.append({"attribute_path": path, "value": value, "source_url": url, "source_section": section, "excerpt": excerpt(ex, 300) if ex else None,
                      "verification_status": status, "method": method})

    # identity: the root is reachable and is the system's official site (seeded from verified registry data)
    attr("identity.official_docs", root.final_url, root.final_url, None, f"HTTP {root.status}; resolved from {seed['url']}")

    # ── discovery ──
    frontier: Dict[str, Tuple[float, int, Optional[str]]] = {}
    def add(u: str, depth: int, parent: Optional[str], title: str = ""):
        cu = canonical_url(u)
        if not cu or not _same_site(cu, host) or cu.lower().endswith(SKIP_EXT) or cu in frontier:
            return
        frontier[cu] = (score(cu, title, depth), depth, parent)

    llms = FETCHER.get(base + "/llms.txt", source_id=sid, parent=root.final_url, depth=1)
    cov["pages_attempted"] += 1
    if llms and llms.ok and "html" not in (llms.headers.get("content-type") or ""):
        cov["pages_ok"] += 1
        for t, u in re.findall(r"\[([^\]]+)\]\(([^)\s]+)\)", llms.text):
            add(urljoin(base + "/", u), 1, base + "/llms.txt", t)
        cov["coverage_notes"].append({"llms_txt": True})
    sm = FETCHER.get(base + "/sitemap.xml", source_id=sid, parent=root.final_url, depth=1)
    cov["pages_attempted"] += 1
    if sm and sm.ok and "<loc>" in sm.text:
        cov["pages_ok"] += 1
        for u in re.findall(r"<loc>\s*(.*?)\s*</loc>", sm.text)[:3000]:
            add(u, 1, base + "/sitemap.xml")
        cov["coverage_notes"].append({"sitemap_urls": len(re.findall(r"<loc>", sm.text))})
    root_page = parse_page(root.text, root.final_url) if "html" in (root.headers.get("content-type") or "text/html") else None
    if root_page:
        for u, t in root_page["links"]:
            add(u, 1, root.final_url, t)

    fetched: Dict[str, Any] = {root.final_url: root}
    pages: Dict[str, Dict[str, Any]] = {root.final_url: root_page} if root_page else {}
    while len(fetched) < max_pages:
        pending = [(v[0], u, v[1], v[2]) for u, v in frontier.items() if u not in fetched and v[1] <= max_depth]
        if not pending:
            break
        pending.sort(reverse=True)
        sc, u, depth, parent = pending[0]
        r = FETCHER.get(u, source_id=sid, parent=parent, depth=depth)
        fetched[u] = r
        cov["pages_attempted"] += 1
        if not r or not r.ok:
            cov["errors"].append(f"{u}: {r.status if r else 'no response'}")
            continue
        cov["pages_ok"] += 1
        if "html" not in (r.headers.get("content-type") or "text/html") and not u.endswith(".md"):
            continue
        p = parse_page(r.text, r.final_url) if not u.endswith(".md") else {"title": u.rsplit("/", 1)[-1], "canonical": None, "text": r.text,
                                                                            "headings": [("h2", h) for h in re.findall(r"^#{1,3}\s+(.+)$", r.text, re.M)][:80],
                                                                            "links": [(urljoin(u, x), t) for t, x in re.findall(r"\[([^\]]+)\]\(([^)\s]+)\)", r.text)],
                                                                            "code": re.findall(r"`([^`]+)`", r.text)[:200], "description": None}
        pages[r.final_url] = p
        if depth < max_depth:
            for lu, lt in p["links"]:
                add(lu, depth + 1, r.final_url, lt)

    # ── per-page records & detectors ──
    thin = 0
    repo_found = None
    packages: Dict[str, str] = {}
    frameworks: Dict[str, Tuple[str, str]] = {}
    components: Dict[str, str] = {}
    for url, p in pages.items():
        if p is None:
            continue
        ts = topics_of(url, p["title"])
        text = p["text"]
        if len(text) < 200:
            thin += 1
        heads = [h for _, h in p["headings"]]
        rec = resource_record(sid, f"page-{url}", (p["title"] or url)[:200], url, summary=p["description"] or excerpt(text, 400), evidence_url=url,
                              kind="official_doc_page", category="C02" if FOUNDATION_TOPICS & set(ts) else "C07" if "accessibility" in ts else
                              "C03" if "tokens" in ts else "C08" if {"contribution", "governance", "releases", "migration", "deprecation"} & set(ts) else
                              "C10" if "theming" in ts else "C05" if "components" in ts else "C09", status="official")
        rec["normalized_content"].update({"topics": ts, "heading_outline": heads[:60], "text_length": len(text), "system_key": sys_key,
                                          "client_rendered_suspected": len(text) < 200})
        rec["design_system"], rec["organization"] = sys_name, org
        rec["evidence_excerpt"] = excerpt(p["description"] or text, 300)
        records.append(rec)
        section = heads[0] if heads else p["title"]
        # Foundations / topical documentation presence (documented = a dedicated official page exists)
        for t in ts:
            if t in FOUNDATION_TOPICS:
                attr(f"foundations.{t}", {"documented": True, "page_title": p["title"]}, url, section, p["description"] or excerpt(text, 200))
        if "tokens" in ts:
            attr("tokens.documented", {"documented": True, "page_title": p["title"]}, url, section, p["description"] or excerpt(text, 200))
            ex = sorted(set(re.findall(r"(?<![\w-])(--[a-z][a-z0-9-]{3,60}|\$[a-z][a-z0-9-]{3,60})", " ".join(p["code"]) + " " + text)))[:12]
            if ex:
                attr("tokens.naming_examples", ex, url, section, ", ".join(ex[:6]))
        if "theming" in ts:
            attr("theming.documented", {"documented": True, "page_title": p["title"]}, url, section, p["description"] or excerpt(text, 200))
        dm = sentence_with(text, r"dark (mode|theme)")
        if dm:
            attr("theming.dark_mode", {"mentioned": True}, url, section, dm)
        if "accessibility" in ts:
            attr("accessibility.documented", {"documented": True, "page_title": p["title"]}, url, section, p["description"] or excerpt(text, 200))
        w = re.search(r"WCAG\s*(2(?:\.\d)?)\s*(?:level\s*)?(AAA|AA|A)\b", text, re.I)
        if w:
            attr("accessibility.wcag_target", f"WCAG {w.group(1)} {w.group(2).upper()}", url, section, sentence_with(text, re.escape(w.group(0))))
        if "accessibility" in ts and re.search(r"keyboard", text, re.I):
            attr("accessibility.keyboard", {"mentioned": True}, url, section, sentence_with(text, r"keyboard"))
        for t, path in (("contribution", "governance.contribution"), ("releases", "governance.releases"), ("migration", "governance.migration"),
                        ("deprecation", "governance.deprecation"), ("browser_support", "technical.browser_support")):
            if t in ts:
                attr(path, {"documented": True, "page_title": p["title"]}, url, section, p["description"] or excerpt(text, 200))
        sv = sentence_with(text, r"semantic versioning|semver")
        if sv:
            attr("governance.versioning", "semantic versioning", url, section, sv)
        # packages & frameworks from installation instructions
        install_text = " ".join(p["code"]) + "\n" + text
        for m in re.finditer(r"(?:npm (?:install|i)|yarn add|pnpm (?:add|install))\s+((?:-{1,2}[\w-]+\s+)*)((?:@?[\w.-]+/)?[\w.-]+)", install_text):
            pkg = m.group(2)
            if pkg.startswith("-") or len(pkg) < 2:
                continue
            packages.setdefault(pkg, url)
        if "installation" in ts or "components" in ts:
            for fw, rx in FRAMEWORK_WORDS.items():
                if fw not in frameworks:
                    sent = sentence_with(text, rx)
                    if sent and re.search(r"install|package|built|support|for\s|using|implementation|library", sent, re.I):
                        frameworks[fw] = (url, sent)
        # repository link published by the official site
        if not repo_found:
            for lu, lt in p["links"]:
                m = re.match(r"https?://(?:www\.)?(github\.com|gitlab\.com)/([\w.-]+)/([\w.-]+)/?$", lu)
                if m and m.group(2).lower() not in ("sponsors", "orgs", "topics", "features", "about", "login", "join"):
                    repo_found = (lu, url)
                    break
        # component inventory from component index pages
        if "components" in ts:
            for lu, lt in p["links"]:
                path = urlparse(lu).path.rstrip("/")
                mm = re.search(r"/components?/([\w-]+)$", path)
                if mm and _same_site(lu, host) and lt and 1 < len(lt) <= 40 and not re.search(r"overview|all components|getting started|introduction|^components?$", lt, re.I):
                    components.setdefault(lt.strip(), canonical_url(lu))

    if repo_found:
        attr("identity.repository", repo_found[0], repo_found[1], None, f"Repository link published on the official site: {repo_found[0]}", status="verified")
        gm = re.match(r"https?://(?:www\.)?github\.com/([\w.-]+)/([\w.-]+)", repo_found[0])
        if gm:
            meta = GITHUB.meta(f"{gm.group(1)}/{gm.group(2)}", sid)
            if meta.get("license") and meta["license"] != "NOASSERTION":
                attr("license", meta["license"], meta.get("html_url") or repo_found[0], "repository metadata", f"SPDX license reported by the GitHub API: {meta['license']}",
                     method="official_repository")
            if meta.get("archived") is not None:
                attr("governance.repository_activity", {"archived": meta["archived"], "pushed_at": meta.get("pushed_at")}, meta.get("html_url") or repo_found[0],
                     "repository metadata", f"archived={meta['archived']}, last push {meta.get('pushed_at')}", method="official_repository")
            elif meta.get("error"):
                cov["limitations"].append(f"GitHub metadata unavailable ({meta['error']}); license not verified.")
    if packages:
        attr("technical.packages", sorted(packages)[:30], next(iter(packages.values())), None, "Install commands: " + ", ".join(sorted(packages)[:8]))
        for pkg, u in packages.items():
            for rx, fw in PKG_FRAMEWORK:
                if re.search(rx, pkg, re.I) and fw not in frameworks:
                    frameworks[fw] = (u, f"Inferred from published package name {pkg}")
                    break
    for fw, (u, sent) in frameworks.items():
        status = "partially_verified" if sent.startswith("Inferred") else "verified"
        attr("technical.frameworks", fw, u, None, sent, status=status, method="official_docs" if status == "verified" else "official_docs_inference")
    if components:
        idx = next((u for u, p in pages.items() if p and "components" in topics_of(u, p["title"])), root.final_url)
        attr("components.inventory", {"count": len(components), "names": sorted(components)[:300]}, idx, None, f"{len(components)} component pages linked from the official component index")

    # system record so the source resolves to the canonical entity (same documentation host)
    srec = make_record("system", sid, sys_key, sys_name or sys_key, summary=f"Official documentation of {sys_name}", primary_category="C12",
                       source_url=root.final_url, extraction_method="html", source_status="official")
    srec.update(organization=org, design_system=sys_name, repository_url=repo_found[0] if repo_found else None)
    srec["normalized_content"] = {"name": sys_name, "organization": org, "documentation_url": root.final_url,
                                  "repository_url": repo_found[0] if repo_found else None, "source_attributes": {"official_docs_root": root.final_url}}
    srec["verification_status"], srec["confidence"] = "verified", "high"
    records.insert(0, srec)
    for name, u in sorted(components.items()):
        c = make_record("component", sid, f"{sys_key}-{name}", f"{sys_name}: {name}", primary_category="C05", source_url=u,
                        extraction_method="html", source_status="official")
        c.update(organization=org, design_system=sys_name)
        c["normalized_content"] = {"component_name": name, "library": sys_name, "documentation_url": u, "detail_level": "doc",
                                   "component_kind": "component", "props_count": 0, "subcomponents": [], "keyboard": [], "accessibility_notes": []}
        c["relationships"] = [{"type": "documented_by_system", "target": srec["record_id"]}]
        c["verification_status"], c["confidence"] = "verified", "high"
        c["notes"].append("Listed in the official component index; the component page itself was not parsed for props in this pass.")
        records.append(c)
    cov["items_found"] = len(pages)
    cov["coverage_notes"].append({"pages_parsed": len(pages), "frontier_size": len(frontier), "thin_pages": thin, "components_listed": len(components),
                                  "attributes": len(attrs)})
    if thin and thin >= max(3, len(pages) // 2):
        cov["limitations"].append(f"{thin}/{len(pages)} pages returned little server-rendered text (client-side rendering suspected); browser rendering was not used.")
    if len(frontier) > len(fetched):
        cov["limitations"].append(f"Crawl stopped at the configured page limit ({max_pages}); {len(frontier) - len(fetched)} discovered URLs not fetched (lower priority).")
    cov["records_emitted"] = len(records)
    cov["crawl_status"] = "inspected" if not cov["errors"] else "inspected_partial"
    return {"records": records, "coverage": cov, "attributes": attrs}
