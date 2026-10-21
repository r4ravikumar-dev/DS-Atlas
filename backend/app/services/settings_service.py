"""Operational settings stored in app_settings with safe defaults (no secrets)."""
from __future__ import annotations

import copy
from typing import Any

from sqlalchemy.orm import Session

from ..models import AppSetting
from ..scrapers.dskb.core import CONFIG

DEFAULTS: dict[str, Any] = {
    "approved_domains": sorted(set(CONFIG.allow_domains)),
    "crawl_defaults": {"max_depth": 3, "max_pages": 600, "per_host_delay_ms": 1000, "timeout_s": 30, "retries": 3, "cache_ttl_hours": 168},
    "retention": {"raw_documents_days": 90, "job_events_days": 30, "exports_hours": 24, "keep_stale_records": True},
    "export_policy": {"min_role": "researcher", "max_rows": 250000, "formats": ["jsonl", "json", "csv", "markdown", "xlsx", "bundle"]},
    "schedule": {"enabled": False, "cron": "0 3 * * 1", "note": "Scheduling is stored but not executed automatically in this version; trigger crawls via the API."},
    "data_quality_rules": {"require_evidence_url": True, "min_sources_for_partial_verification": 2, "flag_conflicting_docs_urls": True},
}


def get_config(db: Session) -> dict[str, Any]:
    out = copy.deepcopy(DEFAULTS)
    for row in db.query(AppSetting).all():
        out[row.key] = row.value
    return out


def update_config(db: Session, changes: dict[str, Any], user_id=None) -> dict[str, Any]:
    for k, v in changes.items():
        if v is None or k not in DEFAULTS:
            continue
        row = db.get(AppSetting, k)
        if row is None:
            db.add(AppSetting(key=k, value=v, updated_by=user_id))
        else:
            row.value, row.updated_by = v, user_id
    db.flush()
    return get_config(db)
