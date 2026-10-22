"""Playground capability and property schemas.

Three tiers:
* live — the installed package at the documented version renders the real component (isolated in its own frame);
* adapter — a platform-rendered preview built from the library's published recipe and this system's stored tokens;
* docs — no faithful preview exists; the API and documentation are shown instead.

Controls come from the component's *documented* props (boolean, literal union, number, string) listed in the registry
(`app/data/playground.json`). Props the implementation accepts but the collected docs don't type as literals are added
from the registry and labelled `implementation`; preview-only text (labels, titles) is labelled `preview`. Defaults keep
their provenance — a preview default is never presented as a documented one.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Component, ComponentProp

REGISTRY_PATH = Path(__file__).resolve().parents[1] / "data" / "playground.json"
NON_LITERAL = re.compile(r"[\[\](){}<>&:=]|=>")


@lru_cache
def registry() -> dict[str, Any]:
    return json.loads(REGISTRY_PATH.read_text())


def recipe_for(library: str | None, name: str) -> dict[str, Any] | None:
    for r in registry()["components"]:
        if r["library"] == library and r["component"] == name:
            return r
    return None


PREVIEWABLE_LEVELS = ("api", "doc")  # directory-index duplicates of a component point at its documented record instead


def tier_for(library: str | None, name: str, detail_level: str | None = "api") -> str:
    r = recipe_for(library, name)
    return registry()["libraries"][r["library"]]["tier"] if r and detail_level in PREVIEWABLE_LEVELS else "docs"


def parse_type(type_text: str | None) -> dict[str, Any] | None:
    """Map a documented TypeScript/markdown type to a control, or None when it can't be controlled safely."""
    if not type_text:
        return None
    t = type_text.replace("\\", "").strip()
    parts = [p.strip() for p in t.split("|") if p.strip() and p.strip() not in ("undefined", "null")]
    if not parts:
        return None
    if all(p == "boolean" or p in ('"true"', '"false"') for p in parts) or (parts[0] == "boolean" and all(p in ("boolean",) or "{" in p or "[" in p for p in parts)):
        return {"kind": "boolean"}
    if parts == ["number"] or (parts[0] == "number" and len(parts) <= 2 and all(p == "number" or "[" in p or "{" in p for p in parts)):
        return {"kind": "number"}
    if parts == ["string"]:
        return {"kind": "string"}
    lits = []
    for p in parts:
        if p in ("string", "number", "boolean") or NON_LITERAL.search(p):
            continue  # a type reference or open type alongside literals: offer the documented literals only
        q = p.strip("`'\"").strip()
        if any(ch in p for ch in "`'\"") and re.fullmatch(r"[A-Za-z0-9][\w\-.%]{0,40}", q):
            lits.append(q)
    lits = list(dict.fromkeys(lits))
    if len(lits) >= 2:
        return {"kind": "enum", "options": lits}
    if "boolean" in parts:
        return {"kind": "boolean"}
    return None


def parse_default(raw: str | None, control: dict[str, Any]) -> tuple[Any, bool]:
    """(value, parsed): a documented default only counts when it is a plain value of the control's kind."""
    if raw is None:
        return None, False
    v = raw.strip().strip("`").strip("'\"").strip()
    k = control["kind"]
    if k == "boolean" and v in ("true", "false"):
        return v == "true", True
    if k == "number" and re.fullmatch(r"-?\d+(\.\d+)?", v):
        return float(v) if "." in v else int(v), True
    if k == "enum" and v in control["options"]:
        return v, True
    if k == "string" and v and len(v) < 60 and not re.search(r"[<>{}]", v):
        return v, True
    return None, False


def _documented(db: Session, c: Component) -> dict[str, ComponentProp]:
    props = db.scalars(select(ComponentProp).where(ComponentProp.component_id == c.id).order_by(ComponentProp.position)).all()
    best: dict[str, ComponentProp] = {}
    own = {c.name, c.name.replace(" ", ""), "Root", "API", None, ""}
    for p in props:
        if p.name not in best or (best[p.name].subcomponent not in own and p.subcomponent in own):
            best[p.name] = p
    return best


def schema(db: Session, c: Component) -> dict[str, Any]:
    reg = registry()
    recipe = recipe_for(c.library, c.name) if c.detail_level in PREVIEWABLE_LEVELS else None
    documented = _documented(db, c)
    base = {"component_id": c.id, "component": c.name, "library": c.library, "system_id": c.system_id,
            "documentation_url": c.documentation_url, "documented_props": len(documented)}
    if not recipe:
        return {**base, "tier": "docs", "implementation": None, "controls": [], "themes": [], "states": [],
                "limitations": ["No faithful preview implementation is available for this component yet. Its documented API and "
                                "official documentation are shown instead."]}
    lib = reg["libraries"][recipe["library"]]
    controls: list[dict[str, Any]] = []
    for name in recipe.get("props", []):
        p = documented.get(name)
        ctl = parse_type(p.type) if p else None
        if not ctl:
            continue
        default, ok = parse_default(p.default_value, ctl)
        preview = (recipe.get("preview") or {}).get(name)
        controls.append({"name": name, **ctl, "description": p.description, "type_text": p.type, "documented": True,
                         "default": default if ok else preview,
                         "default_source": "documented" if ok else ("preview" if preview is not None else None),
                         "documented_default_text": None if ok else p.default_value, "required": bool(p.required and p.required not in ("false", "no"))})
    for name, spec in (recipe.get("extra") or {}).items():
        if any(x["name"] == name for x in controls):
            continue
        p = documented.get(name)
        ctl = {"kind": spec["type"], **({"options": spec["options"]} if "options" in spec else {}),
               **{k: spec[k] for k in ("min", "max", "step") if k in spec}}
        controls.append({"name": name, **ctl, "description": (p.description if p and p.description else spec.get("description")),
                         "type_text": p.type if p else None, "documented": bool(p), "default": spec.get("default"),
                         "default_source": "implementation" if spec.get("default") is not None else None, "documented_default_text": None,
                         "required": False, "provenance": "implementation"})
    for name, text in (recipe.get("content") or {}).items():
        controls.append({"name": name, "kind": "string", "description": "Preview content (sample text, not part of the component's API data).",
                         "type_text": None, "documented": False, "default": text, "default_source": "preview", "documented_default_text": None,
                         "required": False, "provenance": "preview", "max_length": 120})
    for ctl in controls:
        if ctl["kind"] == "number":
            ctl.setdefault("min", -1000)
            ctl.setdefault("max", 1000)
            ctl.setdefault("step", 1)
        ctl.setdefault("provenance", "documented")
    limitations = []
    if lib.get("headless"):
        limitations.append(lib["styling"])
    if lib["tier"] == "adapter":
        limitations.append("Platform-rendered preview, not the original source component. Visual variants follow the library's "
                           "published recipe; behaviour and accessibility parity are not claimed.")
    hidden = [n for n in documented if n not in {x["name"] for x in controls}]
    return {**base, "tier": lib["tier"], "states": recipe.get("states", []), "themes": lib.get("themes", []),
            "implementation": {"key": f"{lib['key']}.{recipe['impl']}", "library_key": lib["key"], "package": lib["package"],
                               "version": lib["version"], "styling": lib["styling"], "headless": bool(lib.get("headless"))},
            "controls": controls, "metadata_only_props": hidden[:60], "metadata_only_count": len(hidden), "limitations": limitations}
