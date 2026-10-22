"""Visual assets that a design system's owner publishes on its own official site: the site icon (SVG / apple-touch /
PNG icon) and the social-preview image (og:image). Found by reading the official page through the polite fetcher
(robots.txt, per-host delay, SSRF checks) and validated by fetching the image itself.

Rules:
* only URLs the official page itself declares are used — nothing is constructed or guessed;
* assets are referenced at their original URL with provenance (page, host, organisation); they are not mirrored,
  because reuse terms are rarely stated. `license` stays null unless the source states it;
* idempotent: an unchanged asset only gets `checked_at` refreshed; a previously good asset that now fails is kept and
  marked `broken` (the public site shows `ok` assets only, the admin sees everything).
"""
from __future__ import annotations

import hashlib
import logging
import re
import struct
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any, Callable
from urllib.parse import urljoin, urlparse

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ..models import DesignSystem, SystemAsset, SystemResource
from ..scrapers.dskb import core as engine
from .evidence_fetch import approve_hosts
from .resources import CODE_HOSTS, TYPE_ORDER, host

log = logging.getLogger(__name__)
MAX_BYTES = 2 * 1024 * 1024
SOURCE_TAG = "ASSETS"


class _Head(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.icons: list[dict[str, str]] = []
        self.meta: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "link" and a.get("href"):
            rel = a.get("rel", "").lower().split()
            if any(r in rel for r in ("icon", "apple-touch-icon", "apple-touch-icon-precomposed")):
                self.icons.append({"href": a["href"], "rel": " ".join(rel), "sizes": a.get("sizes", ""), "type": a.get("type", "")})
        elif tag == "meta":
            key = (a.get("property") or a.get("name") or "").lower()
            if key in ("og:image", "og:image:secure_url", "og:image:alt", "twitter:image", "og:site_name") and a.get("content"):
                self.meta.setdefault(key, a["content"])


def parse_page(html: str, base_url: str) -> dict[str, Any]:
    """Icon candidates (best first) and the social image declared by an HTML page."""
    p = _Head()
    try:
        p.feed(html[:400_000])
    except Exception:  # malformed markup: use whatever was parsed
        pass

    def score(i: dict[str, str]) -> int:
        href, typ = i["href"].lower(), i["type"].lower()
        if typ == "image/svg+xml" or href.split("?")[0].endswith(".svg"):
            return 1000
        if "apple-touch-icon" in i["rel"]:
            return 600
        m = re.findall(r"(\d+)x\d+", i["sizes"])
        size = max(map(int, m)) if m else 16
        return size if not href.split("?")[0].endswith(".ico") else min(size, 32)

    icons = sorted((dict(i, url=urljoin(base_url, i["href"])) for i in p.icons if not i["href"].startswith("data:")), key=score, reverse=True)
    social = p.meta.get("og:image:secure_url") or p.meta.get("og:image") or p.meta.get("twitter:image")
    urls = list(dict.fromkeys(i["url"] for i in icons if i["url"].startswith(("http://", "https://"))))
    return {"icons": urls[:3],
            "social": urljoin(base_url, social) if social and not social.startswith("data:") else None,
            "social_alt": p.meta.get("og:image:alt"), "site_name": p.meta.get("og:site_name")}


def image_size(data: bytes, mime: str) -> tuple[int | None, int | None]:
    """Intrinsic size from PNG / GIF / JPEG / SVG headers (no image library needed)."""
    try:
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            return struct.unpack(">II", data[16:24])
        if data[:6] in (b"GIF87a", b"GIF89a"):
            return struct.unpack("<HH", data[6:10])
        if data[:2] == b"\xff\xd8":
            i = 2
            while i < len(data) - 9:
                if data[i] != 0xFF:
                    i += 1
                    continue
                marker, seg = data[i + 1], struct.unpack(">H", data[i + 2:i + 4])[0]
                if marker in (0xC0, 0xC1, 0xC2):
                    h, w = struct.unpack(">HH", data[i + 5:i + 9])
                    return w, h
                i += 2 + seg
        if "svg" in mime or data.lstrip()[:5] in (b"<svg ", b"<?xml"):
            t = data[:4000].decode("utf8", "ignore")
            vb = re.search(r'viewBox="\s*[-\d.]+[ ,]+[-\d.]+[ ,]+([\d.]+)[ ,]+([\d.]+)', t)
            if vb:
                return round(float(vb.group(1))), round(float(vb.group(2)))
    except Exception:
        pass
    return None, None


def sniff(data: bytes) -> str | None:
    head = data[:16]
    if head.startswith(b"\x89PNG"):
        return "image/png"
    if head.startswith(b"\xff\xd8"):
        return "image/jpeg"
    if head[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if head[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if head[:4] == b"\x00\x00\x01\x00":
        return "image/x-icon"
    if data.lstrip()[:4] in (b"<svg", b"<?xm") and b"<svg" in data[:2000]:
        return "image/svg+xml"
    return None


def _fetch_image(url: str) -> dict[str, Any]:
    approve_hosts([url])
    r = engine.FETCHER.get(url, source_id=SOURCE_TAG, timeout=15, retries=1)
    if r is None:
        return {"ok": False, "error": "not fetched (robots, policy or network)"}
    if r.status != 200:
        return {"ok": False, "error": f"HTTP {r.status}"}
    mime = (r.headers.get("content-type") or r.headers.get("Content-Type") or "").split(";")[0].strip().lower()
    if not mime.startswith("image/"):
        mime = sniff(r.content) or ""  # some CDNs serve images as octet-stream: trust the bytes, not the label
    if not mime:
        return {"ok": False, "error": "not an image"}
    if len(r.content) > MAX_BYTES or len(r.content) < 64:
        return {"ok": False, "error": f"unexpected size ({len(r.content)} bytes)"}
    w, h = image_size(r.content, mime)
    return {"ok": True, "url": r.final_url or url, "mime": mime, "bytes": len(r.content), "width": w, "height": h,
            "sha": hashlib.sha256(r.content).hexdigest()}


def _official_page(db: Session, system_id: int) -> SystemResource | None:
    rows = db.scalars(select(SystemResource).where(SystemResource.system_id == system_id, SystemResource.verification_status != "invalid",
                                                   SystemResource.resource_type.in_(["official_website", "official_documentation"]))).all()
    own = [r for r in rows if not CODE_HOSTS.search(host(r.url))]
    own.sort(key=lambda r: (not r.is_primary, r.verification_status != "verified", TYPE_ORDER.index(r.resource_type)))
    return own[0] if own else None


def _discover(system: DesignSystem, page_url: str) -> dict[str, Any]:
    url = re.sub(r"^http://", "https://", page_url)
    approve_hosts([url])
    r = engine.FETCHER.get(url, source_id=SOURCE_TAG, timeout=15, retries=1)
    if r is None or r.status != 200:
        return {"system_id": system.id, "page": page_url, "error": f"official page unavailable ({'HTTP ' + str(r.status) if r else 'not fetched'})"}
    found = parse_page(r.text, r.final_url or url)
    out: dict[str, Any] = {"system_id": system.id, "page": r.final_url or url, "candidates": []}
    for icon in found["icons"]:
        img = _fetch_image(icon)
        out["candidates"].append(("icon", icon, img, None))
        if img.get("ok"):
            break  # best valid icon only
    if found["social"]:
        out["candidates"].append(("social_image", found["social"], _fetch_image(found["social"]), found["social_alt"]))
    return out


def collect(db: Session, *, system_ids: list[int] | None = None, progress: Callable[[int, int, str], None] | None = None, workers: int = 6) -> dict[str, Any]:
    q = select(DesignSystem).order_by(DesignSystem.id)
    if system_ids:
        q = q.where(DesignSystem.id.in_(system_ids))
    systems = db.scalars(q).all()
    targets = [(s, p.url) for s in systems if (p := _official_page(db, s.id))]
    summary = {"systems": len(systems), "with_official_page": len(targets), "assets_new": 0, "assets_changed": 0, "assets_unchanged": 0,
               "assets_broken": 0, "pages_unavailable": 0}
    now = datetime.now(timezone.utc)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for n, res in enumerate(ex.map(lambda t: _discover(*t), targets), 1):
            s = db.get(DesignSystem, res["system_id"])
            if progress:
                progress(n, len(targets), s.name)
            if res.get("error"):
                summary["pages_unavailable"] += 1
                continue
            page_host = urlparse(res["page"]).netloc.lower().removeprefix("www.")
            seen: set[tuple[str, str]] = set()
            for kind, url, img, alt in res["candidates"]:
                if (kind, img.get("url") or url) in seen:
                    continue
                seen.add((kind, img.get("url") or url))
                row = db.scalar(select(SystemAsset).where(SystemAsset.system_id == s.id, SystemAsset.kind == kind, SystemAsset.url == (img.get("url") or url)))
                if not img.get("ok"):
                    summary["assets_broken"] += 1
                    if row:
                        row.status, row.error, row.checked_at = "broken", img.get("error"), now
                    else:
                        db.add(SystemAsset(system_id=s.id, kind=kind, url=url, page_url=res["page"], source_host=page_host, status="broken",
                                           error=img.get("error"), checked_at=now, source_organization=s.organization))
                        db.flush()
                    continue
                if row and row.content_sha256 == img["sha"] and row.status == "ok":
                    row.checked_at = now
                    summary["assets_unchanged"] += 1
                    continue
                summary["assets_changed" if row else "assets_new"] += 1
                row = row or SystemAsset(system_id=s.id, kind=kind, url=img["url"])
                if row.id is None:
                    db.add(row)
                    db.flush()
                row.page_url, row.source_host, row.source_organization = res["page"], page_host, s.organization
                row.mime, row.width, row.height, row.bytes, row.content_sha256 = img["mime"], img["width"], img["height"], img["bytes"], img["sha"]
                row.alt = (alt or "").strip()[:400] or (f"{s.name} icon" if kind == "icon" else f"Preview image published on {page_host}")
                row.attribution = f"© {s.organization or page_host}. Published at {res['page']}"
                row.status, row.error, row.retrieved_at, row.checked_at = "ok", None, now, now
            db.flush()
            _choose_primary(db, s.id)
            db.commit()  # per system, so a long run keeps its progress
    return summary


def _choose_primary(db: Session, system_id: int) -> None:
    rows = db.scalars(select(SystemAsset).where(SystemAsset.system_id == system_id)).all()
    for kind in {r.kind for r in rows}:
        ok = sorted((r for r in rows if r.kind == kind and r.status == "ok"), key=lambda r: (r.mime != "image/svg+xml", -(r.width or 0), r.id))
        best = ok[0].id if ok else None
        for r in rows:
            if r.kind == kind and r.is_primary != (r.id == best):
                r.is_primary = r.id == best


def public_assets(db: Session, ids: list[int]) -> dict[int, dict[str, dict[str, Any]]]:
    """Primary `ok` assets per system: {system_id: {"icon": {...}, "social_image": {...}}}. A site icon only counts as a
    logo when it is a vector or at least 64 px — tiny favicons look broken when enlarged, so the monogram is used instead."""
    out: dict[int, dict[str, dict[str, Any]]] = {i: {} for i in ids}
    if not ids:
        return out
    for a in db.scalars(select(SystemAsset).where(SystemAsset.system_id.in_(ids), SystemAsset.is_primary.is_(True), SystemAsset.status == "ok")):
        if a.kind == "icon" and a.mime != "image/svg+xml" and (a.width or 0) < 64:
            continue
        out[a.system_id][a.kind] = {"url": a.url, "alt": a.alt, "width": a.width, "height": a.height, "page_url": a.page_url,
                                    "source_host": a.source_host, "attribution": a.attribution, "license": a.license}
    return out
