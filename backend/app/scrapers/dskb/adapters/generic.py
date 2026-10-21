"""Generic adapter for user-registered sources: bounded same-host breadth-first discovery.
Emits one resource record per page (title, description, heading outline) — conservative by design."""
from __future__ import annotations

from collections import deque
from typing import Any, Dict, List
from urllib.parse import urlparse

from ..core import FETCHER, canonical_url, excerpt
from .common import abs_links, new_coverage, page_meta, probe_seed, resource_record, soup_of

SKIP_EXT = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".pdf", ".zip", ".mp4", ".css", ".js", ".ico", ".woff", ".woff2")


def run_generic(seed: Dict[str, Any]) -> Dict[str, Any]:
    sid = seed["source_id"]
    max_pages = int(seed.get("max_pages") or 50)
    max_depth = int(seed.get("max_depth") or 2)
    cov = new_coverage(seed)
    cov["extraction_method"] = f"html breadth-first discovery (same host, depth ≤ {max_depth}, ≤ {max_pages} pages)"
    cov["provides"] = "unknown"
    records: List[Dict[str, Any]] = []
    root = probe_seed(seed, cov)
    if not root or not root.ok:
        cov["records_emitted"] = 0
        return {"records": records, "coverage": cov}
    host = urlparse(root.final_url).netloc
    seen = {canonical_url(root.final_url)}
    queue = deque([(root.final_url, root, 0)])
    while queue and len(seen) <= max_pages:
        url, resp, depth = queue.popleft()
        if resp is None:
            resp = FETCHER.get(url, source_id=sid, depth=depth)
            cov["pages_attempted"] += 1
            if not resp or not resp.ok:
                cov["errors"].append(f"{url}: {resp.status if resp else 'no response'}")
                continue
            cov["pages_ok"] += 1
        if "html" not in (resp.headers.get("content-type") or "text/html"):
            continue
        meta = page_meta(resp.text, resp.final_url)
        s = soup_of(resp.text)
        heads = [h.get_text(" ", strip=True) for h in s.find_all(["h1", "h2", "h3"])][:40]
        rec = resource_record(sid, resp.final_url, (meta["title"] or resp.final_url)[:200], resp.final_url,
                              summary=meta["description"], evidence_url=resp.final_url, kind="page", category="C12", status="unknown")
        rec["normalized_content"]["heading_outline"] = heads
        rec["evidence_excerpt"] = excerpt(meta["description"] or " ".join(heads), 300)
        records.append(rec)
        if depth >= max_depth:
            continue
        for link, _ in abs_links(resp.text, resp.final_url):
            cu = canonical_url(link)
            if urlparse(link).netloc != host or cu in seen or cu.lower().endswith(SKIP_EXT):
                continue
            if len(seen) >= max_pages:
                break
            seen.add(cu)
            queue.append((link, None, depth + 1))
    cov["items_found"] = len(records)
    cov["records_emitted"] = len(records)
    if len(seen) >= max_pages:
        cov["limitations"].append(f"Stopped at the configured page limit ({max_pages}).")
    return {"records": records, "coverage": cov}
