"""Tell the public site which cached pages to refresh after a build that changed content.

Only called when something actually changed (a no-change daily sync never touches the site's cache). Failures are
logged and swallowed: the site's own time-based revalidation still bounds staleness to a few minutes.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from ..core.config import get_settings

log = logging.getLogger(__name__)

KIND_TAG = {"systems": "system", "components": "component", "tokens": "token"}
MAX_ENTITY_TAGS = 150


def tags_for(summary: dict[str, Any]) -> list[str]:
    """Cache tags for the public pages a build's changes affect; empty when nothing changed."""
    changes = summary.get("changes") or {}
    changed_kinds = [k for k, c in changes.items() if k != "relationships" and any(c.get(x) for x in ("created", "updated", "removed"))]
    rel = changes.get("relationships") or {}
    if not changed_kinds and not (rel.get("added") or rel.get("removed")):
        return []
    tags = ["stats", "search", *changed_kinds]
    ids = summary.get("changed_ids") or {}
    entity = [f"{KIND_TAG[k]}:{i}" for k in KIND_TAG for i in ids.get(k, [])]
    # beyond a handful, the broad kind tags already cover everything
    return tags + (entity if len(entity) <= MAX_ENTITY_TAGS else [])


def notify(summary: dict[str, Any]) -> bool:
    cfg = get_settings()
    url, secret = cfg.frontend_revalidate_url, cfg.revalidate_secret
    tags = tags_for(summary)
    if not (url and secret and tags):
        return False
    try:
        r = httpx.post(url, json={"tags": tags}, headers={"Authorization": f"Bearer {secret.get_secret_value()}"}, timeout=10)
        r.raise_for_status()
        log.info("frontend cache refreshed", extra={"tags": len(tags)})
        return True
    except Exception as e:  # never fail a build because the site is unreachable
        log.warning("frontend cache refresh failed: %s", type(e).__name__)
        return False
