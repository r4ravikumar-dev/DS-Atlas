"""Helpers shared by adapters: seed probing, HTML parsing, coverage bookkeeping."""
from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..core import FETCHER, Response, canonical_url, excerpt, make_record, now_iso


def soup_of(html: str) -> BeautifulSoup:
    s = BeautifulSoup(html, "lxml")
    return s


def page_meta(html: str, base: str) -> Dict[str, Optional[str]]:
    s = soup_of(html)
    def m(**attrs):
        t = s.find("meta", attrs=attrs)
        return t.get("content") if t else None
    can = s.find("link", rel="canonical")
    return {
        "title": (s.title.get_text(strip=True) if s.title else None),
        "description": m(name="description") or m(property="og:description"),
        "canonical": urljoin(base, can["href"]) if can and can.get("href") else None,
        "generator": m(name="generator"),
    }


def visible_text(html: str) -> str:
    s = soup_of(html)
    for t in s(["script", "style", "svg", "noscript", "template"]):
        t.decompose()
    return (s.find("main") or s.body or s).get_text("\n", strip=True)


def new_coverage(seed: Dict[str, str]) -> Dict[str, Any]:
    return {
        "source_id": seed["source_id"], "name": seed["name"], "original_url": seed["url"], "resolved_url": None,
        "source_type": seed["source_type"], "crawl_status": "pending", "http_status": None, "page_title": None,
        "meta_description": None, "canonical_url": None, "last_modified": None, "access_restrictions": [],
        "robots": None, "extraction_method": None, "pages_attempted": 0, "pages_ok": 0, "items_found": 0,
        "records_emitted": 0, "coverage_notes": [], "limitations": [], "errors": [], "last_checked_at": now_iso(),
        "provides": None,  # original | links | mixed
        "version_context": {},
    }


def probe_seed(seed: Dict[str, str], cov: Dict[str, Any]) -> Optional[Response]:
    r = FETCHER.get(seed["url"], source_id=seed["source_id"], depth=0)
    cov["pages_attempted"] += 1
    from urllib.parse import urlparse
    base = f"{urlparse(seed['url']).scheme}://{urlparse(seed['url']).netloc}"
    cov["robots"] = FETCHER.robots_raw.get(base)
    if r is None:
        cov["crawl_status"] = "failed_or_blocked"
        cov["errors"].append("Seed request returned no response (blocked by robots, network failure, or not allow-listed)")
        return None
    cov["http_status"] = r.status
    cov["resolved_url"] = r.final_url
    cov["last_modified"] = r.headers.get("last-modified")
    if r.ok and "html" in (r.headers.get("content-type") or ""):
        meta = page_meta(r.text, r.final_url)
        cov["page_title"], cov["meta_description"], cov["canonical_url"] = meta["title"], meta["description"], meta["canonical"]
    if r.ok:
        cov["pages_ok"] += 1
        cov["crawl_status"] = "inspected"
    else:
        cov["crawl_status"] = f"http_{r.status}"
    return r


def fetch_many(urls: List[Tuple[str, Optional[str], int]], source_id: str, cov: Dict[str, Any], workers: int = 1) -> Dict[str, Optional[Response]]:
    """Fetch (url, parent, depth) tuples. Per-host politeness is enforced inside the fetcher, so
    workers > 1 only helps when URLs span several hosts."""
    out: Dict[str, Optional[Response]] = {}

    def one(t):
        u, parent, depth = t
        return u, FETCHER.get(u, source_id=source_id, parent=parent, depth=depth)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        for u, r in ex.map(one, urls):
            cov["pages_attempted"] += 1
            if r is not None and r.ok:
                cov["pages_ok"] += 1
            else:
                cov["errors"].append(f"{u}: {'no response' if r is None else r.status}")
            out[u] = r
    return out


def resource_record(source_id: str, key: str, title: str, url: str, *, summary=None, category="C12", method="html",
                    evidence_url: str, kind: str = "resource", status="third_party", **kw) -> Dict[str, Any]:
    rec = make_record("resource", source_id, key, title, summary=excerpt(summary, 600), primary_category=category,
                      source_url=evidence_url, extraction_method=method, source_status=status, **kw)
    rec["normalized_content"] = {"resource_kind": kind, "destination_url": url, "destination_canonical": canonical_url(url)}
    return rec


def system_record(source_id: str, key: str, name: str, *, organization=None, evidence_url: str, method="html",
                  docs_url=None, repo_url=None, storybook_url=None, figma_url=None, description=None,
                  attributes: Optional[Dict[str, Any]] = None, frameworks=None, **kw) -> Dict[str, Any]:
    rec = make_record("system", source_id, key, name if not organization else f"{organization} — {name}",
                      summary=excerpt(description, 600), primary_category="C12", source_url=evidence_url,
                      extraction_method=method, source_status="third_party", **kw)
    rec["organization"] = organization
    rec["design_system"] = name
    rec["repository_url"] = repo_url
    rec["frameworks"] = frameworks or []
    rec["normalized_content"] = {
        "name": name, "organization": organization, "documentation_url": docs_url,
        "documentation_canonical": canonical_url(docs_url), "repository_url": repo_url, "storybook_url": storybook_url,
        "design_resource_url": figma_url, "description": description, "source_attributes": attributes or {},
    }
    rec["verification_status"] = "unverified"
    rec["notes"].append("Directory listing: a discovery record, not verification of the system's own documentation.")
    return rec


def abs_links(html: str, base: str) -> List[Tuple[str, str]]:
    s = soup_of(html)
    out = []
    for a in s.find_all("a", href=True):
        h = a["href"].strip()
        if h.startswith(("mailto:", "javascript:", "#", "tel:")):
            continue
        out.append((urljoin(base, h), a.get_text(" ", strip=True)))
    return out


def gh_full_name(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    m = re.match(r"https?://github\.com/([\w.-]+)/([\w.-]+)", url)
    if not m or m.group(1) in ("orgs", "topics", "sponsors", "features", "marketplace"):
        return None
    repo = m.group(2)[:-4] if m.group(2).endswith(".git") else m.group(2)
    return f"{m.group(1)}/{repo}"
