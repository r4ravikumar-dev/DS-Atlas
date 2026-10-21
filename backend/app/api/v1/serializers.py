from __future__ import annotations

from typing import Any

from ...models import Component, DesignToken, Guideline
from ...scrapers.dskb.sources import TAXONOMY


def component_out(c: Component, source_key: str) -> dict[str, Any]:
    d = {k: getattr(c, k) for k in ("id", "name", "family", "library", "system_id", "detail_level", "kind", "description", "documentation_url",
                                    "props_count", "keyboard_count", "a11y_count", "frameworks", "verification_status", "source_version")}
    d["source_key"] = source_key
    return d


def token_out(t: DesignToken, source_key: str) -> dict[str, Any]:
    d = {k: getattr(t, k) for k in ("id", "name", "path", "group", "type", "type_inferred", "raw_value", "resolved_value", "alias_of", "theme",
                                    "platform", "component", "description", "source_format", "design_system_name", "system_id", "verification_status", "source_version")}
    d["source_key"] = source_key
    return d


def guideline_out(g: Guideline, source_key: str) -> dict[str, Any]:
    d = {k: getattr(g, k) for k in ("id", "record_type", "kind", "title", "category", "summary", "section", "priority", "design_system_name",
                                    "confidence", "verification_status", "review_status")}
    d["category_name"] = TAXONOMY.get(g.category, {}).get("name", g.category)
    d["source_key"] = source_key
    return d
