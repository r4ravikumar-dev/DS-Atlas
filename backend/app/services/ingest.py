"""Persist one source's adapter output idempotently.

* Records are upserted by their deterministic `record_key` (re-crawls update, never duplicate).
* Each record keeps an evidence row linking its source URL to the stored raw document when available.
* Records of this source not re-observed by a successful crawl are marked `is_stale` (kept, not deleted).
* Source status/coverage reflect the adapter's documented outcome (never "fully scraped" by default)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from ..models import DiscoveredUrl, Evidence, Record, Source
from ..scrapers.dskb import pipeline as engine

RECORD_COLUMNS = {"record_type", "title", "summary", "primary_category", "secondary_categories", "tags", "source_url",
                  "organization", "source_version", "source_status", "extraction_method", "confidence", "verification_status",
                  "frameworks", "technologies", "license", "content_hash"}
EXTRA_KEYS = ("canonical_url", "repository_url", "source_file_path", "source_section", "evidence_excerpt", "notes", "relationships",
              "category_name", "platforms", "duplicate_group_id", "schema_version")
INSPECTED = {"inspected", "inspected_partial", "unavailable_seed__substitute_extracted"}


def _unique_keys(records: list[dict[str, Any]]) -> None:
    seen: dict[str, int] = {}
    for r in records:
        k = r["record_id"]
        if k in seen:
            seen[k] += 1
            r["record_id"] = f"{k}~{seen[k]}"
        else:
            seen[k] = 1


def ingest(db: Session, src: Source, job_id, result: dict[str, Any]) -> dict[str, Any]:
    records, cov = result.get("records", []), result.get("coverage", {})
    engine.normalize(records)
    engine.categorize(records)
    _unique_keys(records)
    now = datetime.now(timezone.utc)

    raw_by_url = {}
    for url, final, raw_id in db.execute(select(DiscoveredUrl.url, DiscoveredUrl.final_url, DiscoveredUrl.raw_document_id)
                                         .where(DiscoveredUrl.source_id == src.id, DiscoveredUrl.raw_document_id.is_not(None))):
        raw_by_url[url] = raw_id
        if final:
            raw_by_url.setdefault(final, raw_id)

    rows = []
    for r in records:
        nc = r.get("normalized_content") or {}
        row = {k: r.get(k) for k in RECORD_COLUMNS}
        row.update(record_key=r["record_id"], source_id=src.id, design_system_name=r.get("design_system"), content=nc,
                   extra={k: r.get(k) for k in EXTRA_KEYS if r.get(k) not in (None, [], {})},
                   frameworks=r.get("frameworks") or [], technologies=r.get("technologies") or [], secondary_categories=r.get("secondary_categories") or [],
                   tags=r.get("tags") or [], is_stale=False, last_seen_job_id=job_id, first_seen_job_id=job_id, last_verified_at=now)
        row["title"] = (row["title"] or r["record_id"])[:5000]
        row["source_url"] = row["source_url"] or src.url
        rows.append(row)

    ids: dict[str, int] = {}
    for i in range(0, len(rows), 500):
        chunk = rows[i:i + 500]
        stmt = insert(Record).values(chunk)
        upd = {c: stmt.excluded[c] for c in chunk[0] if c not in ("record_key", "first_seen_job_id")}
        upd["updated_at"] = func.now()
        res = db.execute(stmt.on_conflict_do_update(index_elements=["record_key"], set_=upd).returning(Record.id, Record.record_key))
        ids.update({k: v for v, k in res.all()})

    ev_rows = []
    for r in records:
        rid = ids.get(r["record_id"])
        if not rid:
            continue
        url = r.get("source_url") or src.url
        ev_rows.append({"record_id": rid, "url": url, "excerpt": r.get("evidence_excerpt"), "source_file_path": r.get("source_file_path"),
                        "source_section": r.get("source_section"), "source_version": r.get("source_version"),
                        "raw_document_id": raw_by_url.get(url), "captured_at": now})
    for i in range(0, len(ev_rows), 1000):
        stmt = insert(Evidence).values(ev_rows[i:i + 1000])
        db.execute(stmt.on_conflict_do_update(constraint="uq_evidence_record_url", set_={
            "excerpt": stmt.excluded.excerpt, "source_section": stmt.excluded.source_section, "source_version": stmt.excluded.source_version,
            "raw_document_id": func.coalesce(stmt.excluded.raw_document_id, Evidence.raw_document_id), "captured_at": stmt.excluded.captured_at}))

    status = cov.get("crawl_status") or "unknown"
    stale = 0
    if records and status in INSPECTED:
        stale = db.execute(update(Record).where(Record.source_id == src.id, Record.last_seen_job_id != job_id, Record.is_stale.is_(False))
                           .values(is_stale=True)).rowcount or 0

    src.status = status
    src.http_status = cov.get("http_status")
    src.resolved_url = cov.get("resolved_url")
    src.page_title = cov.get("page_title")
    src.robots = cov.get("robots") or {}
    src.coverage = {k: cov.get(k) for k in ("extraction_method", "provides", "items_found", "records_emitted", "coverage_notes", "limitations",
                                             "errors", "version_context", "discovered_substitute", "duration_s", "access_restrictions")}
    src.pages_attempted = int(cov.get("pages_attempted") or 0)
    src.pages_ok = int(cov.get("pages_ok") or 0)
    src.error_count = len(cov.get("errors") or [])
    src.records_count = db.scalar(select(func.count()).select_from(Record).where(Record.source_id == src.id, Record.is_stale.is_(False))) or 0
    src.last_attempted_at = now
    if status in INSPECTED:
        src.last_success_at = now
    db.flush()
    return {"records_upserted": len(ids), "records_marked_stale": stale, "crawl_status": status, "errors": len(cov.get("errors") or [])}
