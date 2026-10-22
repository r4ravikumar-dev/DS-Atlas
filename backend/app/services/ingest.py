"""Persist one source's adapter output idempotently.

* Records are keyed by their deterministic `record_key` (re-crawls update, never duplicate).
* Change detection: each record carries a `fingerprint` of its stored content. Unchanged records are not written at all
  (no new version, `content_updated_at` untouched); changed records are updated and logged in `record_changes`.
  A missing fingerprint (rows from before change tracking) is filled in as a baseline, not counted as a change.
* Each created/changed record keeps an evidence row linking its source URL to the stored raw document when available.
* Records of this source not re-observed are marked `is_stale` (kept, not deleted) — but only after a complete,
  error-free crawl and only when the drop is plausible; otherwise staling is suppressed and reported (temporary outages,
  blocked pages or moved routes must never hide valid data).
* Source status/coverage reflect the adapter's documented outcome (never "fully scraped" by default)."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from ..models import DiscoveredUrl, Evidence, Record, RecordChange, Source
from ..scrapers.dskb import pipeline as engine

RECORD_COLUMNS = {"record_type", "title", "summary", "primary_category", "secondary_categories", "tags", "source_url",
                  "organization", "source_version", "source_status", "extraction_method", "confidence", "verification_status",
                  "frameworks", "technologies", "license", "content_hash"}
EXTRA_KEYS = ("canonical_url", "repository_url", "source_file_path", "source_section", "evidence_excerpt", "notes", "relationships",
              "category_name", "platforms", "duplicate_group_id", "schema_version")
INSPECTED = {"inspected", "inspected_partial", "unavailable_seed__substitute_extracted"}
CONTENT_FIELDS = sorted((RECORD_COLUMNS - {"content_hash"}) | {"content", "extra", "design_system_name"})
# Staling more than this share of a source's active records in one crawl needs a human: it is far more likely an outage,
# a redesign that broke extraction, or a blocked crawler than a real mass removal.
MAX_STALE_SHARE = 0.3


def fingerprint(row: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps({k: row.get(k) for k in CONTENT_FIELDS}, sort_keys=True, default=str, ensure_ascii=False).encode()).hexdigest()


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

    for row in rows:
        row["fingerprint"] = fingerprint(row)
    existing = {k: (i, fp, st) for i, k, fp, st in db.execute(
        select(Record.id, Record.record_key, Record.fingerprint, Record.is_stale).where(Record.record_key.in_([r["record_key"] for r in rows])))} \
        if rows else {}
    sync_run_id = (result.get("context") or {}).get("sync_run_id")
    ids: dict[str, int] = {k: v[0] for k, v in existing.items()}
    created = updated = unchanged = restored = baselined = 0
    changes: list[dict[str, Any]] = []
    new_rows = [r for r in rows if r["record_key"] not in existing]
    for i in range(0, len(new_rows), 500):
        res = db.execute(insert(Record).values([{**r, "content_updated_at": now} for r in new_rows[i:i + 500]])
                         .on_conflict_do_nothing(index_elements=["record_key"]).returning(Record.id, Record.record_key))
        for rid, k in res.all():
            ids[k] = rid
            created += 1
    for r in new_rows:
        if r["record_key"] in ids:
            changes.append({"record_key": r["record_key"], "record_type": r["record_type"], "change": "created", "title": r["title"][:500]})
    changed_keys: set[str] = {r["record_key"] for r in new_rows}
    for r in rows:
        if r["record_key"] not in existing:
            continue
        rid, old_fp, was_stale = existing[r["record_key"]]
        content = {k: v for k, v in r.items() if k not in ("record_key", "first_seen_job_id", "source_id")}
        if old_fp is None:  # baseline from before change tracking: adopt the fingerprint, do not call it a change
            db.execute(update(Record).where(Record.id == rid).values(fingerprint=r["fingerprint"], last_seen_job_id=job_id, is_stale=False))
            baselined += 1
        elif old_fp != r["fingerprint"]:
            db.execute(update(Record).where(Record.id == rid).values(**content, content_updated_at=now))
            updated += 1
            changed_keys.add(r["record_key"])
            changes.append({"record_key": r["record_key"], "record_type": r["record_type"], "change": "updated", "title": r["title"][:500]})
            continue
        else:
            unchanged += 1
        if was_stale:  # seen again with identical content: visible again, content untouched
            db.execute(update(Record).where(Record.id == rid).values(is_stale=False, last_seen_job_id=job_id))
            restored += 1
            changes.append({"record_key": r["record_key"], "record_type": r["record_type"], "change": "restored", "title": r["title"][:500]})

    # provenance for created/changed records (unchanged records keep their existing evidence rows untouched)
    ev_rows = []
    for r in records:
        rid = ids.get(r["record_id"])
        if not rid or r["record_id"] not in changed_keys:
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
    stale = stale_suppressed = 0
    seen = {r["record_key"] for r in rows}
    active = dict(db.execute(select(Record.record_key, Record.record_type).where(Record.source_id == src.id, Record.is_stale.is_(False))).all())
    missing = [k for k in active if k not in seen]
    stale_note = None
    if missing:
        complete = bool(records) and status == "inspected" and not cov.get("errors")
        plausible = len(missing) <= max(5, int(MAX_STALE_SHARE * len(active)))
        if complete and plausible:
            for i in range(0, len(missing), 1000):
                stale += db.execute(update(Record).where(Record.record_key.in_(missing[i:i + 1000]), Record.is_stale.is_(False))
                                    .values(is_stale=True)).rowcount or 0
            changes += [{"record_key": k, "record_type": active[k], "change": "staled", "title": None} for k in missing]
        else:
            stale_suppressed = len(missing)
            stale_note = ("crawl incomplete or had errors" if not complete else
                          f"{len(missing)} of {len(active)} records missing (> {int(MAX_STALE_SHARE * 100)}%): kept for review")
    if changes:
        for i in range(0, len(changes), 1000):
            db.execute(insert(RecordChange), [{**c, "job_id": job_id, "sync_run_id": sync_run_id, "source_id": src.id} for c in changes[i:i + 1000]])

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
        src.consecutive_failures = 0
    else:
        src.consecutive_failures = (src.consecutive_failures or 0) + 1
    # source-level fingerprint over its active records: unchanged content ⇒ identical hash across runs
    fps = db.execute(select(Record.record_key, Record.fingerprint).where(Record.source_id == src.id, Record.is_stale.is_(False))
                     .order_by(Record.record_key)).all()
    source_hash = hashlib.sha256("\n".join(f"{k}:{f}" for k, f in fps).encode()).hexdigest()
    content_changed = bool(created or updated or stale or restored) or (src.last_content_hash not in (None, source_hash) and not baselined)
    summary = {"records_seen": len(rows), "records_created": created, "records_updated": updated, "records_unchanged": unchanged + baselined,
               "records_restored": restored, "records_marked_stale": stale, "stale_suppressed": stale_suppressed, "stale_note": stale_note,
               "fingerprints_baselined": baselined, "content_changed": content_changed}
    if content_changed:
        src.last_content_changed_at = now
    src.last_content_hash = source_hash
    src.last_change_summary = {**summary, "checked_at": now.isoformat(), "job_id": str(job_id)}
    db.flush()
    return {"records_upserted": created + updated, **summary, "crawl_status": status, "errors": len(cov.get("errors") or [])}
