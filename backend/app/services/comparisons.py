"""Comparison generation from persisted records. Every cell carries a status:
documented (value from a cited source) | not_documented (field empty in inspected sources) | not_applicable.
Analytical observations are returned separately under `interpretation`."""
from __future__ import annotations

import re
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core.exceptions import AppError
from ..models import Comparison, Component, ComponentProp, DesignSystem, DesignToken, Guideline, Record

SYSTEM_DIMENSIONS = ["overview", "frameworks", "tokens", "accessibility", "styling", "governance", "components", "sources", "maintenance"]
COMPONENT_DIMENSIONS = ["overview", "api", "state", "keyboard", "accessibility", "structure", "evidence"]
STATE_PROP = re.compile(r"^(default)?(open|opened|value|checked|selected|selectedKeys?|isOpen|isSelected|expanded|expandedKeys|activeKey|pressed)$", re.I)
HANDLER = re.compile(r"^on((Open|Value|Checked|Pressed|Selection|Expanded|Active|Input)?Change|Close|Cancel|Ok)$")


def cell(value: Any, evidence: list[str] | None = None, na: bool = False) -> dict[str, Any]:
    if na:
        return {"status": "not_applicable", "value": None, "evidence": []}
    empty = value in (None, "", [], {}, 0)
    return {"status": "not_documented" if empty else "documented", "value": None if empty else value, "evidence": (evidence or [])[:5]}


def _systems(db: Session, ids: list[int], dims: list[str]) -> dict[str, Any]:
    systems = {s.id: s for s in db.scalars(select(DesignSystem).where(DesignSystem.id.in_(ids)))}
    missing = [i for i in ids if i not in systems]
    if missing:
        raise AppError(f"Unknown design-system ids: {missing}", code="VALIDATION_ERROR", status_code=422)
    cols, rows = [], {}
    for i in ids:
        s = systems[i]
        ev = (s.attributes or {}).get("evidence_urls", [])
        fams = db.execute(select(Component.family, func.count()).where(Component.system_id == i, Component.family.is_not(None))
                          .group_by(Component.family).order_by(func.count().desc()).limit(12)).all()
        tok_types = db.execute(select(DesignToken.type, func.count()).where(DesignToken.system_id == i).group_by(DesignToken.type)
                               .order_by(func.count().desc()).limit(8)).all()
        cols.append({"id": i, "name": s.name, "organization": s.organization, "verification_status": s.verification_status})
        data = {
            "overview": {"Documentation": cell(s.documentation_url, ev), "Repository": cell(s.repository_url, ev), "Storybook": cell(s.storybook_url, ev),
                         "Description": cell(s.description, ev)},
            "frameworks": {"Frameworks": cell(s.frameworks, ev), "Framework evidence": cell((s.attributes or {}).get("framework_evidence"))},
            "tokens": {"Token architecture": cell(s.token_architecture, ev), "Token records": cell(s.token_count),
                       "Token types": cell({t or "unknown": n for t, n in tok_types})},
            "accessibility": {"Accessibility documentation": cell(s.accessibility_documentation, ev)},
            "styling": {"Styling strategy": cell(s.styling_strategy, ev)},
            "governance": {"Governance": cell(s.governance, ev)},
            "components": {"Component records": cell(s.component_count), "Top families": cell({f: n for f, n in fams})},
            "sources": {"Independent sources": cell(s.source_count), "Source IDs": cell(s.source_keys), "Verification": cell(s.verification_basis),
                        "Conflicts": cell(s.conflicts or None)},
            "maintenance": {"Last verified": cell(s.last_verified_at.isoformat() if s.last_verified_at else None), "Deprecated flag": cell(s.deprecated or None),
                            "AI-readiness score": cell(s.ai_readiness)},
        }
        for d in dims:
            rows.setdefault(d, {})
            for label, c in data[d].items():
                rows[d].setdefault(label, []).append(c)
    shared_fw = set.intersection(*[set(systems[i].frameworks or []) for i in ids]) if ids else set()
    interp = []
    if shared_fw:
        interp.append(f"All compared systems list support for: {', '.join(sorted(shared_fw))} (directory-reported unless verified).")
    gaps = [label for d in rows for label, cs in rows[d].items() if all(c["status"] == "not_documented" for c in cs)]
    if gaps:
        interp.append(f"No compared system has extracted data for: {', '.join(gaps[:8])}. Treat as unknown, not absent.")
    return {"columns": cols, "dimensions": dims, "rows": rows, "interpretation": interp}


def _components(db: Session, ids: list[int], dims: list[str]) -> dict[str, Any]:
    comps = {c.id: c for c in db.scalars(select(Component).where(Component.id.in_(ids)))}
    missing = [i for i in ids if i not in comps]
    if missing:
        raise AppError(f"Unknown component ids: {missing}", code="VALIDATION_ERROR", status_code=422)
    cols, rows, prop_sets = [], {}, {}
    for i in ids:
        c = comps[i]
        rec = db.get(Record, c.record_id)
        nc = rec.content or {}
        props = db.scalars(select(ComponentProp).where(ComponentProp.component_id == i).order_by(ComponentProp.position)).all()
        names = [p.name for p in props]
        prop_sets[i] = set(names)
        ev = [rec.source_url] + ([c.documentation_url] if c.documentation_url else [])
        headless = c.library in ("Radix Primitives", "Base UI", "React Aria")
        cols.append({"id": i, "name": c.name, "library": c.library, "family": c.family, "verification_status": c.verification_status})
        data = {
            "overview": {"Library": cell(c.library, ev), "Kind": cell(c.kind), "Detail level": cell(c.detail_level), "Description": cell(c.description, ev),
                         "Version inspected": cell(c.source_version)},
            "api": {"Documented props": cell(len(names), ev), "Subcomponents": cell([s.get("name") for s in nc.get("subcomponents", [])], ev),
                    "Variants (from source)": cell(nc.get("variants_from_source"), ev)},
            "state": {"State props": cell(sorted({n for n in names if STATE_PROP.match(n)}), ev),
                      "Change handlers": cell(sorted({n for n in names if HANDLER.match(n)}), ev)},
            "keyboard": {"Keyboard entries": cell([f"{k.get('keys')}: {k.get('description')}" for k in (nc.get("keyboard") or [])][:12], ev)},
            "accessibility": {"Accessibility notes": cell([a.get("section") for a in (nc.get("accessibility_notes") or [])], ev),
                              "ARIA pattern links": cell(nc.get("aria_pattern_links"), ev)},
            "structure": {"Anatomy documented": cell(bool(nc.get("has_anatomy_section")) or None, ev), "Data attributes": cell(len(nc.get("data_attributes") or []) or None),
                          "CSS variables": cell([v.get("variable") for v in (nc.get("css_variables") or [])][:10], ev, na=False),
                          "Styling tokens": cell(None, na=headless) if headless else cell(len(nc.get("styles_api") or []) or None, ev)},
            "evidence": {"Source URL": cell(rec.source_url), "Documentation URL": cell(c.documentation_url)},
        }
        for d in dims:
            rows.setdefault(d, {})
            for label, cl in data[d].items():
                rows[d].setdefault(label, []).append(cl)
    common = set.intersection(*prop_sets.values()) if prop_sets else set()
    interp = []
    if len({comps[i].family for i in ids}) > 1:
        interp.append("The selected components belong to different families; API differences may reflect different purposes.")
    if common:
        interp.append(f"Props documented by every compared component: {', '.join(sorted(common)[:20])}.")
    hl = [comps[i].library for i in ids if comps[i].library in ("Radix Primitives", "Base UI", "React Aria")]
    if hl:
        interp.append(f"{', '.join(sorted(set(hl)))} are headless: visual styling/tokens are intentionally out of scope (not applicable, not missing).")
    return {"columns": cols, "dimensions": dims, "rows": rows, "interpretation": interp,
            "shared_props": sorted(common), "prop_matrix": {str(i): sorted(prop_sets[i])[:200] for i in ids}}


def compute(db: Session, kind: str, ids: list[int], dims: list[str] | None = None) -> dict[str, Any]:
    """Read-only comparison (nothing persisted) — used by the public compare view."""
    allowed = SYSTEM_DIMENSIONS if kind == "systems" else COMPONENT_DIMENSIONS
    dims = dims or allowed
    bad = [d for d in dims if d not in allowed]
    if bad:
        raise AppError(f"Unsupported dimensions: {bad}", code="VALIDATION_ERROR", status_code=422, details=[{"field": "dimensions", "reason": f"allowed: {allowed}"}])
    return {"kind": kind, "dimensions": dims, "result": (_systems if kind == "systems" else _components)(db, ids, dims)}


def generate(db: Session, comp: Comparison) -> Comparison:
    dims = comp.dimensions or (SYSTEM_DIMENSIONS if comp.kind == "systems" else COMPONENT_DIMENSIONS)
    allowed = SYSTEM_DIMENSIONS if comp.kind == "systems" else COMPONENT_DIMENSIONS
    bad = [d for d in dims if d not in allowed]
    if bad:
        raise AppError(f"Unsupported dimensions: {bad}", code="VALIDATION_ERROR", status_code=422, details=[{"field": "dimensions", "reason": f"allowed: {allowed}"}])
    comp.result = (_systems if comp.kind == "systems" else _components)(db, list(comp.item_ids), dims)
    comp.dimensions = dims
    comp.status = "generated"
    comp.generated_at = datetime.now(timezone.utc)
    db.flush()
    return comp
