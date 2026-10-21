"""Source registry: seeding the 20 mandatory sources, validation of user-registered sources, coverage."""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core.exceptions import AppError, Conflict, NotFound
from ..models import DiscoveredUrl, Record, Source
from ..scrapers.dskb.core import canonical_url, is_public_host
from ..scrapers.dskb.sources import SEEDS
from . import settings_service


def seed_sources(db: Session) -> int:
    """Idempotently register the mandatory seed sources (S01–S20)."""
    n = 0
    for s in SEEDS:
        row = db.scalar(select(Source).where(Source.key == s["source_id"]))
        if row is None:
            db.add(Source(key=s["source_id"], name=s["name"], url=s["url"], canonical_url=canonical_url(s["url"]),
                          domain=urlparse(s["url"]).netloc.lower(), source_type=s["source_type"], adapter=s["adapter"], origin="seed"))
            n += 1
        else:
            row.name, row.url, row.adapter, row.source_type = s["name"], s["url"], s["adapter"], s["source_type"]
    db.flush()
    return n


def get(db: Session, source_id: int) -> Source:
    s = db.get(Source, source_id)
    if not s:
        raise NotFound("Source not found.")
    return s


def _domain_approved(domain: str, approved: list[str]) -> bool:
    return any(domain == d or domain.endswith("." + d) for d in approved)


def create(db: Session, *, name: str, url: str, source_type: str, max_pages: int, max_depth: int) -> Source:
    p = urlparse(url)
    if p.scheme != "https":
        raise AppError("Only https:// sources can be registered.", code="VALIDATION_ERROR", status_code=422,
                       details=[{"field": "url", "reason": "scheme must be https"}])
    if p.username or p.password or (p.port not in (None, 443)):
        raise AppError("URLs with credentials or non-standard ports are not allowed.", code="VALIDATION_ERROR", status_code=422,
                       details=[{"field": "url", "reason": "credentials/port not allowed"}])
    domain = p.hostname.lower() if p.hostname else ""
    approved = settings_service.get_config(db)["approved_domains"]
    if not _domain_approved(domain, approved):
        raise AppError(f"Domain '{domain}' is not in the approved-domain list. An administrator must approve it first (Settings → Approved domains).",
                       code="DOMAIN_NOT_APPROVED", status_code=422, details=[{"field": "url", "reason": "domain not approved"}])
    if not is_public_host(domain):
        raise AppError("The URL resolves to a non-public network address.", code="UNSAFE_DESTINATION", status_code=422,
                       details=[{"field": "url", "reason": "private, loopback, link-local or metadata address"}])
    cu = canonical_url(url)
    if db.scalar(select(Source).where(Source.canonical_url == cu)):
        raise Conflict("A source with this URL is already registered.")
    n = (db.scalar(select(func.count()).select_from(Source).where(Source.origin == "user")) or 0) + 1
    src = Source(key=f"U{n:03d}", name=name, url=url, canonical_url=cu, domain=domain, source_type=source_type, adapter="generic",
                 origin="user", crawl_limits={"max_pages": max_pages, "max_depth": max_depth})
    db.add(src)
    db.flush()
    return src


def coverage(db: Session, src: Source) -> dict[str, Any]:
    by_type = dict(db.execute(select(Record.record_type, func.count()).where(Record.source_id == src.id, Record.is_stale.is_(False))
                              .group_by(Record.record_type)).all())
    by_outcome = dict(db.execute(select(DiscoveredUrl.outcome, func.count()).where(DiscoveredUrl.source_id == src.id)
                                 .group_by(DiscoveredUrl.outcome)).all())
    cov = src.coverage or {}
    return {"source_id": src.id, "key": src.key, "status": src.status, "pages_attempted": src.pages_attempted, "pages_ok": src.pages_ok,
            "records_by_type": by_type, "urls_by_outcome": by_outcome, "limitations": cov.get("limitations", []),
            "errors": (cov.get("errors") or [])[:50], "version_context": cov.get("version_context") or {}, "last_success_at": src.last_success_at}
