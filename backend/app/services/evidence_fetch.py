"""Fetch a page as evidence through the polite engine fetcher (robots, SSRF guard, per-host delay, cache)
and summarize what it proves: final URL after redirects, HTTP status, canonical link, title, outbound hosts."""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from ..scrapers.dskb import core as engine

SOURCE_TAG = "VERIFY"


def host_path(url: str | None, segments: int = 1) -> str | None:
    if not url:
        return None
    p = urlparse(engine.canonical_url(url) or url)
    host = p.netloc.lower().removeprefix("www.")
    segs = [s for s in p.path.split("/") if s]
    return host + ("/" + "/".join(segs[:segments]) if segs and segments else "")


def approve_hosts(urls: list[str | None]) -> set[str]:
    hosts = {urlparse(u).netloc.lower() for u in urls if u and u.startswith("http")}
    engine.FETCHER.extra_allow |= hosts
    return hosts


def fetch_evidence(url: str | None) -> dict[str, Any]:
    if not url or not url.startswith("http"):
        return {"url": url, "ok": False, "error": "no URL"}
    # Prefer https for directory URLs recorded as http (the fetcher re-validates every redirect).
    target = re.sub(r"^http://", "https://", url)
    r = engine.FETCHER.get(target, source_id=SOURCE_TAG, timeout=12, retries=1)
    if r is None and target != url:
        r = engine.FETCHER.get(url, source_id=SOURCE_TAG, timeout=12, retries=1)
    if r is None:
        return {"url": url, "ok": False, "error": "no response (robots/SSRF/allow-list/network)", "checked_at": engine.now_iso()}
    out: dict[str, Any] = {"url": url, "final_url": r.final_url, "status": r.status, "ok": r.ok, "checked_at": r.fetched_at,
                           "content_sha256": r.content_sha256, "from_cache": r.from_cache}
    if r.ok and "html" in (r.headers.get("content-type") or "text/html"):
        s = BeautifulSoup(r.text[:2_000_000], "lxml")
        can = s.find("link", rel="canonical")
        out["canonical"] = urljoin(r.final_url, can["href"]) if can and can.get("href") else None
        out["title"] = s.title.get_text(strip=True)[:200] if s.title else None
        links = {urljoin(r.final_url, a["href"]) for a in s.find_all("a", href=True) if a["href"].startswith(("http", "/"))}
        out["outbound"] = sorted({host_path(l, 2) for l in links if l.startswith("http")} - {None})[:400]
        out["text_len"] = len(s.get_text(" ", strip=True))
    elif r.ok and "markdown" in (r.headers.get("content-type") or "") or url.endswith((".md", "README")):
        links = re.findall(r"https?://[^\s)>\]\"']+", r.text)
        out["outbound"] = sorted({host_path(l, 2) for l in links} - {None})[:400]
    return out


def links_to(ev: dict[str, Any], target_url: str | None) -> bool:
    """True when an evidence page links to the target's host(+first path segment)."""
    if not target_url or not ev.get("outbound"):
        return False
    t1 = host_path(target_url, 1)
    return bool(t1) and any(o == t1 or o.startswith(t1 + "/") for o in ev["outbound"])
