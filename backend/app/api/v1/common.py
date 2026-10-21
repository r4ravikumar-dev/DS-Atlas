from __future__ import annotations

import math
from typing import Any

from fastapi import Query

from ...schemas import ErrorResponse

ERRORS = {401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}}


def page_out(items: list[Any], total: int, page: int, page_size: int, extra_meta: dict | None = None) -> dict[str, Any]:
    meta = {"page": page, "page_size": page_size, "total_items": total, "total_pages": max(1, math.ceil(total / page_size)) if page_size else 1}
    if extra_meta:
        meta.update(extra_meta)
    return {"data": items, "meta": meta}


def csv_list(name: str, description: str = ""):
    """Repeatable or comma-separated list query parameter."""
    def dep(v: list[str] | None = Query(None, alias=name, description=description or f"Filter by {name} (repeatable or comma-separated)")) -> list[str] | None:
        if not v:
            return None
        out = [x.strip() for item in v for x in item.split(",") if x.strip()]
        return out[:50] or None
    return dep
