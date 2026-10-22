"""Public presentation model for read endpoints.

Anonymous (and non-admin) readers get the research content without internal operational metadata: verification and
confidence states, review/deduplication status, crawl and extraction diagnostics, internal source keys and link-check
details. The data is unchanged in the database and an administrator session receives full responses — this is a
presentation rule applied in one place, not a destructive change.

`require("public:read")` marks the request (`request.state.public_view`); the HTTP middleware in `main.py` applies
`project()` to the JSON body of those responses.
"""
from __future__ import annotations

from typing import Any

INTERNAL_FIELDS = frozenset({
    # verification, confidence, review and deduplication state
    "verification_status", "verification_basis", "verification_coverage", "verification_method", "verification", "verified",
    "confidence", "review_status", "conflicts", "merged_aliases", "requested_alias", "last_verified_at",
    # crawl / extraction / link-check diagnostics
    "evidence_note", "http_status", "access_note", "last_checked_at", "origin", "extraction_status", "resolution_status",
    "type_inferred", "detail_level", "is_stale", "stale", "interpretation_note", "value_note", "method",
    # internal identifiers and raw ingestion structures
    "source_key", "source_keys", "record_key", "raw_document_id", "attributes",
})
# Under these paths "status"/"limitation" describe crawl outcomes (elsewhere "status" can be content, e.g. comparison cells).
STATUS_PATHS = ("/storybook",)


def _clean(v: Any, drop_status: bool) -> Any:
    if isinstance(v, list):
        return [_clean(x, drop_status) for x in v if not (isinstance(x, dict) and x.get("verification_status") == "invalid" and "resource_type" in x)]
    if isinstance(v, dict):
        return {k: _clean(x, drop_status) for k, x in v.items()
                if k not in INTERNAL_FIELDS and not (drop_status and k in ("status", "limitation", "limitations", "confidence"))}
    return v


def project(path: str, body: Any) -> Any:
    return _clean(body, any(p in path for p in STATUS_PATHS))
