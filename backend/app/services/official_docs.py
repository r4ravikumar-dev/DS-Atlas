"""Selects the most-cited systems for official-documentation verification and registers them as `official` sources."""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import AttributeEvidence, Component, DesignSystem, Source
from ..scrapers.dskb.core import canonical_url, is_public_host

LIBRARY_SOURCES = {"S11", "S12", "S13", "S14", "S15", "S16"}  # already crawled from official docs as seed sources
DIRECTORY_SOURCES = {"S01", "S02", "S03", "S04", "S05", "S06", "S07", "S08", "S17", "S18", "S20"}


def priority_table(db: Session, limit: int = 15) -> list[dict[str, Any]]:
    """Rank by independent directory coverage (distinct seed sources), then by missing verification."""
    rows = []
    ev = dict(db.execute(select(AttributeEvidence.system_key, func.count(func.distinct(AttributeEvidence.attribute_path))).group_by(AttributeEvidence.system_key)).all())
    for d in db.scalars(select(DesignSystem).where(DesignSystem.documentation_url.is_not(None))):
        srcs = set(d.source_keys or [])
        if srcs & LIBRARY_SOURCES:
            continue
        indep = len(srcs & DIRECTORY_SOURCES)
        rows.append({"system_key": d.key, "system_id": d.id, "name": d.name, "organization": d.organization, "independent_sources": indep,
                     "sources": sorted(srcs), "official_docs_url": d.official_docs_url or d.documentation_url, "verification_status": d.verification_status,
                     "attributes_with_evidence": ev.get(d.key, 0), "components_known": d.component_count,
                     "score": indep * 10 - min(ev.get(d.key, 0), 20) * 0.5})
    rows.sort(key=lambda r: (-r["score"], r["name"].lower()))
    for i, r in enumerate(rows[:limit], 1):
        r["rank"] = i
        r["selected"] = True
        r["selection_reason"] = f"{r['independent_sources']} independent directory sources; {r['attributes_with_evidence']} attributes already evidenced"
    return rows[:limit]


def register(db: Session, table: list[dict[str, Any]], max_pages: int = 45) -> list[Source]:
    out = []
    n = db.scalar(select(func.count()).select_from(Source).where(Source.origin == "official")) or 0
    for r in table:
        url = r["official_docs_url"].replace("http://", "https://", 1)
        existing = db.scalar(select(Source).where(Source.origin == "official", Source.system_key == r["system_key"]))
        if existing:
            out.append(existing)
            continue
        host = urlparse(url).hostname or ""
        if not is_public_host(host):
            continue
        n += 1
        src = Source(key=f"O{n:02d}", name=f"{r['name']} — official documentation", url=url, canonical_url=canonical_url(url), domain=host,
                     source_type="official_documentation", adapter="official_docs", origin="official", system_key=r["system_key"],
                     crawl_limits={"max_pages": max_pages, "max_depth": 3, "system_name": r["name"], "organization": r["organization"],
                                   "selection": {k: r[k] for k in ("rank", "independent_sources", "selection_reason")}})
        db.add(src)
        db.flush()
        out.append(src)
    return out
