"""Crawl handler: connects a registered source to its engine adapter, persists every fetch
(discovered_urls + content-addressed raw documents), streams progress to the job row, and ingests records."""
from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert

from ..database.session import SessionLocal
from ..models import DiscoveredUrl, Job, RawDocument, Source
from ..scrapers.dskb import core as engine_core
from ..scrapers.dskb.adapters import directories, generic, libraries, official_docs, repos
from ..scrapers.dskb.sources import SEED_BY_ID
from ..services import ingest, jobs as jobsvc, settings_service
from ..services.storage import storage

ADAPTERS = {
    "surf": directories.run_surf, "adele": directories.run_adele, "dsrepo": directories.run_dsrepo, "storybook": directories.run_storybook,
    "dsdir": directories.run_dsdir, "dsguide": directories.run_dsguide, "dscom": directories.run_dscom, "dsone": directories.run_dsone,
    "awesome": repos.run_awesome, "style_dictionary": repos.run_style_dictionary, "dtcg": repos.run_dtcg, "checklist": repos.run_checklist,
    "shadcn": libraries.run_shadcn, "radix": libraries.run_radix, "baseui": libraries.run_baseui, "reactaria": libraries.run_reactaria,
    "mantine": libraries.run_mantine, "antd": libraries.run_antd, "generic": generic.run_generic,
    "official_docs": official_docs.run_official_docs,
}
OK_OUTCOMES = {"fetched", "cache_hit", "not_modified"}
ERR_OUTCOMES = {"http_error", "failed", "blocked_robots", "blocked_unsafe_destination"}
_config_lock = threading.Lock()


class FetchRecorder:
    """Fetch listener for one job. Thread-safe; batches progress heartbeats; raises JobCancelled on request."""

    def __init__(self, job_id, source_db_id: int):
        self.job_id, self.source_db_id = job_id, source_db_id
        self.lock = threading.Lock()
        self.urls: set[str] = set()
        self.ok = self.err = 0
        self.last_beat = 0.0
        self.cancelled = False

    def __call__(self, event: dict[str, Any], resp) -> None:
        outcome = event.get("outcome")
        if outcome == "retry":
            return
        url = event["url"]
        raw_id = None
        with SessionLocal() as db:
            if resp is not None and resp.ok and resp.content:
                sha = resp.content_sha256 or engine_core.sha256(resp.content)
                key = storage().put(f"raw/{sha[:2]}/{sha}", resp.content)
                stmt = insert(RawDocument).values(content_sha256=sha, storage_key=key, content_type=(resp.headers or {}).get("content-type"),
                                                  size_bytes=len(resp.content), first_url=url)
                raw_id = db.execute(stmt.on_conflict_do_update(index_elements=["content_sha256"], set_={"storage_key": stmt.excluded.storage_key})
                                    .returning(RawDocument.id)).scalar_one()
            vals = dict(parent_url=event.get("parent"), depth=int(event.get("depth") or 0), outcome=outcome, http_status=event.get("status"),
                        final_url=event.get("final_url"), content_type=event.get("content_type"), raw_document_id=raw_id, last_job_id=self.job_id,
                        error=(event.get("error") or None))
            stmt = insert(DiscoveredUrl).values(source_id=self.source_db_id, url=url, **vals)
            upd = {**vals, "fetch_count": DiscoveredUrl.fetch_count + 1, "updated_at": func.now()}
            if raw_id is None:
                upd.pop("raw_document_id")
            db.execute(stmt.on_conflict_do_update(constraint="uq_discovered_source_url", set_=upd))
            db.commit()
        with self.lock:
            self.urls.add(url)
            if outcome in OK_OUTCOMES:
                self.ok += 1
            elif outcome in ERR_OUTCOMES:
                self.err += 1
            beat = time.time() - self.last_beat > 2
            if beat:
                self.last_beat = time.time()
        if beat:
            with SessionLocal() as db:
                if jobsvc.heartbeat(db, self.job_id, phase="fetching", urls_discovered=len(self.urls), urls_processed=self.ok, error_count=self.err):
                    self.cancelled = True
        if self.cancelled:
            raise engine_core.JobCancelled()


def _seed_for(src: Source) -> dict[str, Any]:
    if src.origin == "seed" and src.key in SEED_BY_ID:
        return dict(SEED_BY_ID[src.key])
    if src.origin == "official":
        lim = src.crawl_limits or {}
        return {"source_id": src.key, "name": src.name, "url": src.url, "source_type": src.source_type, "adapter": src.adapter,
                "system_key": src.system_key, "system_name": lim.get("system_name"), "organization": lim.get("organization"),
                "max_pages": lim.get("max_pages", 45), "max_depth": lim.get("max_depth", 3)}
    return {"source_id": src.key, "name": src.name, "url": src.url, "source_type": src.source_type, "adapter": src.adapter,
            "max_pages": (src.crawl_limits or {}).get("max_pages", 30), "max_depth": (src.crawl_limits or {}).get("max_depth", 2)}


def run_crawl(job: Job) -> None:
    with SessionLocal() as db:
        src = db.get(Source, job.source_id)
        if src is None:
            jobsvc.finish(db, job.id, "failed", error="source no longer exists")
            return
        if src.is_paused:
            jobsvc.finish(db, job.id, "cancelled", error="source is paused")
            return
        cfg = settings_service.get_config(db)
        seed = _seed_for(src)
        jobsvc.add_event(db, job.id, f"Crawling {src.key} {src.name} with adapter '{seed['adapter']}'", phase="fetching",
                         data={"url": src.url, "approved_domains": len(cfg["approved_domains"])})
        db.commit()
        src_id, key = src.id, src.key

    defaults = cfg["crawl_defaults"]
    with _config_lock:  # engine fetcher is process-global; config is applied before adapters run
        f = engine_core.FETCHER
        f.extra_allow = set(cfg["approved_domains"])
        f.cfg.per_host_delay = max(0.5, float(defaults.get("per_host_delay_ms", 1000)) / 1000)
        f.cfg.timeout = float(defaults.get("timeout_s", 30))
        f.cfg.retries = int(defaults.get("retries", 3))
        f.cfg.cache_ttl_hours = float(defaults.get("cache_ttl_hours", 168))
        f.cfg.refresh = bool((job.params or {}).get("refresh"))
    rec = FetchRecorder(job.id, src_id)
    engine_core.FETCHER.listeners[key] = rec
    t0 = time.time()
    try:
        result = ADAPTERS[seed["adapter"]](seed)
    except engine_core.JobCancelled:
        with SessionLocal() as db:
            jobsvc.finish(db, job.id, "cancelled", error="cancelled by user", urls_discovered=len(rec.urls), urls_processed=rec.ok, error_count=rec.err)
        return
    finally:
        engine_core.FETCHER.listeners.pop(key, None)

    cov = result.get("coverage", {})
    cov["duration_s"] = round(time.time() - t0, 1)
    with SessionLocal() as db:
        jobsvc.heartbeat(db, job.id, phase="ingesting", urls_discovered=len(rec.urls), urls_processed=rec.ok, error_count=rec.err)
        src = db.get(Source, src_id)
        summary = ingest.ingest(db, src, job.id, result)
        if result.get("attributes"):
            summary["attributes_recorded"] = persist_attributes(db, src, job.id, result["attributes"])
        jobsvc.add_event(db, job.id, f"Ingested {summary['records_upserted']} records ({summary['records_marked_stale']} marked stale)", phase="ingesting", data=summary)
        db.commit()
        status = cov.get("crawl_status")
        if status == "inspected" and not cov.get("errors"):
            final = "succeeded"
        elif status in ("inspected", "inspected_partial", "unavailable_seed__substitute_extracted") or summary["records_upserted"]:
            final = "partially_succeeded"
        else:
            final = "failed"
        jobsvc.finish(db, job.id, final, error=None if final != "failed" else "; ".join((cov.get("errors") or ["no records extracted"])[:3])[:2000],
                      result={**summary, "limitations": cov.get("limitations", []), "coverage_notes": cov.get("coverage_notes", [])},
                      urls_discovered=len(rec.urls), urls_processed=rec.ok, error_count=rec.err, records_extracted=summary["records_upserted"])


def persist_attributes(db, src: Source, job_id, attrs: list[dict[str, Any]]) -> int:
    """Upsert field-level evidence (idempotent per system/attribute/URL/value)."""
    import hashlib
    import json as _json
    from ..models import AttributeEvidence
    rows = {}
    for a in attrs:
        val = _json.dumps(a.get("value"), sort_keys=True, default=str)
        key = hashlib.sha256(f"{src.system_key}|{a['attribute_path']}|{a['source_url']}|{val}".encode()).hexdigest()
        rows[key] = dict(evidence_key=key, system_key=src.system_key, attribute_path=a["attribute_path"], value=a.get("value"), source_url=a["source_url"],
                         source_section=(a.get("source_section") or None), source_version=a.get("source_version"), excerpt=a.get("excerpt"),
                         verification_status=a.get("verification_status", "verified"), method=a.get("method", "official_docs"), source_id=src.id, job_id=job_id,
                         checked_at=datetime.now(timezone.utc))
    if not rows:
        return 0
    stmt = insert(AttributeEvidence).values(list(rows.values()))
    db.execute(stmt.on_conflict_do_update(index_elements=["evidence_key"], set_={"excerpt": stmt.excluded.excerpt, "checked_at": stmt.excluded.checked_at,
                                                                                  "job_id": stmt.excluded.job_id, "verification_status": stmt.excluded.verification_status}))
    return len(rows)
