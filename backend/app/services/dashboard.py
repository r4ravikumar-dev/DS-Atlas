"""Dashboard aggregates (computed server-side from persisted data)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from ..models import (
    AttributeEvidence, Component, DesignSystem, DesignToken, DiscoveredUrl,
    DuplicateGroup, Guideline, Job, Record, Source, StorybookProject,
    StorybookStory, StorybookVariant
)
from ..scrapers.dskb.sources import TAXONOMY

OK_STATUSES = ("inspected", "inspected_partial", "unavailable_seed__substitute_extracted")


def summary(db: Session) -> dict[str, Any]:
    c = lambda stmt: db.scalar(stmt) or 0  # noqa: E731
    total = c(select(func.count()).select_from(Source))
    inspected = c(select(func.count()).select_from(Source).where(Source.status.in_(("inspected", "inspected_partial"))))
    never = c(select(func.count()).select_from(Source).where(Source.status == "never_crawled"))
    recs = c(select(func.count()).select_from(Record).where(Record.is_stale.is_(False)))
    with_ev = c(text("SELECT count(DISTINCT r.id) FROM records r JOIN evidence e ON e.record_id = r.id WHERE NOT r.is_stale"))
    verified = c(select(func.count()).select_from(Record).where(Record.is_stale.is_(False), Record.verification_status == "verified"))
    with_raw = c(text("SELECT count(DISTINCT e.record_id) FROM evidence e WHERE e.raw_document_id IS NOT NULL"))
    return {
        "sources_total": total, "sources_inspected": inspected, "sources_never_crawled": never,
        "sources_failed": total - inspected - never,
        "urls_discovered": c(select(func.count()).select_from(DiscoveredUrl)),
        "pages_processed": c(select(func.count()).select_from(DiscoveredUrl).where(DiscoveredUrl.outcome.in_(("fetched", "cache_hit", "not_modified")))),
        "design_systems": c(select(func.count()).select_from(DesignSystem)),
        "systems_multi_source": c(select(func.count()).select_from(DesignSystem).where(DesignSystem.source_count >= 2)),
        "components": c(select(func.count()).select_from(Component)),
        "components_with_api": c(select(func.count()).select_from(Component).where(Component.props_count > 0)),
        "tokens": c(select(func.count()).select_from(DesignToken)),
        "guidelines": c(select(func.count()).select_from(Guideline).where(Guideline.record_type.in_(("guideline", "specification")))),
        "patterns": c(select(func.count()).select_from(Guideline).where(Guideline.record_type == "pattern")),
        "storybook_projects": c(select(func.count()).select_from(StorybookProject)),
        "storybook_stories": c(select(func.count()).select_from(StorybookStory)),
        "storybook_variants": c(select(func.count()).select_from(StorybookVariant)),
        "attribute_evidence": c(select(func.count()).select_from(AttributeEvidence)),
        "review_open": c(select(func.count()).select_from(DuplicateGroup).where(DuplicateGroup.review_status == "open")),
        "stale_records": c(select(func.count()).select_from(Record).where(Record.is_stale.is_(True))),
        "jobs_running": c(select(func.count()).select_from(Job).where(Job.status.in_(("running", "queued")))),
        "last_crawl_at": db.scalar(select(func.max(Source.last_attempted_at))),
        "quality": {"records": recs, "with_evidence_pct": round(100 * with_ev / recs, 1) if recs else 0.0,
                    "with_raw_snapshot_pct": round(100 * with_raw / recs, 1) if recs else 0.0,
                    "verified_pct": round(100 * verified / recs, 1) if recs else 0.0},
    }


def activity(db: Session, days: int = 30, limit: int = 20) -> dict[str, Any]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    jobs = db.scalars(select(Job).where(Job.created_at >= since).order_by(Job.created_at.desc()).limit(limit)).all()
    recent = db.execute(select(Record.id, Record.record_type, Record.title, Record.updated_at, Source.key).join(Source, Source.id == Record.source_id)
                        .where(Record.is_stale.is_(False)).order_by(Record.updated_at.desc()).limit(limit)).all()
    per_day = db.execute(text("""SELECT date_trunc('day', created_at)::date d, status, count(*) FROM jobs WHERE created_at >= :s
                                 GROUP BY 1, 2 ORDER BY 1"""), {"s": since}).all()
    return {"jobs": jobs, "recent_records": [dict(id=a, record_type=b, title=c_, updated_at=d, source_key=e) for a, b, c_, d, e in recent],
            "jobs_per_day": [{"date": str(d), "status": s, "count": n} for d, s, n in per_day]}


def source_coverage(db: Session) -> list[dict[str, Any]]:
    rows = db.execute(text("""
      SELECT s.id, s.key, s.name, s.status, s.pages_attempted, s.pages_ok, s.error_count, s.last_success_at,
             (SELECT count(*) FROM records r WHERE r.source_id = s.id AND NOT r.is_stale) AS records,
             (SELECT count(*) FROM discovered_urls u WHERE u.source_id = s.id) AS urls
      FROM sources s ORDER BY s.key""")).mappings().all()
    return [dict(r) for r in rows]


def category_distribution(db: Session) -> list[dict[str, Any]]:
    rows = db.execute(select(Record.primary_category, Record.record_type, func.count()).where(Record.is_stale.is_(False))
                      .group_by(Record.primary_category, Record.record_type)).all()
    out: dict[str, dict[str, Any]] = {}
    for cat, rt, n in rows:
        d = out.setdefault(cat, {"category": cat, "name": TAXONOMY.get(cat, {}).get("name", cat), "total": 0, "by_type": {}})
        d["total"] += n
        d["by_type"][rt] = n
    return sorted(out.values(), key=lambda d: d["category"])
