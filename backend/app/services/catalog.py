"""Navigational structure of the canonical dataset: stable slugs, the component-family taxonomy and token categories.

`refresh(db)` runs after every build (and via `manage.py refresh-catalog`). It only fills what is missing or derivable:
* slugs are assigned once and never rewritten, so public URLs stay stable across rebuilds and daily syncs;
* token category/tier are recomputed deterministically and written only where they differ (a no-change sync writes nothing);
* families are upserted from the taxonomy below.
None of this changes research content, fingerprints or `content_updated_at`.
"""
from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from typing import Any, Iterable

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from ..models import Component, ComponentFamily, DesignSystem, DesignToken, Guideline
from ..scrapers.dskb.sources import COMPONENT_FAMILIES

# ── component-family taxonomy ─────────────────────────────────────────────────────────────────────────────────────────
CATEGORIES: list[tuple[str, str]] = [
    ("Actions", "Elements that trigger an action or navigation."),
    ("Forms and input", "Controls that collect or edit user input."),
    ("Navigation", "Moving between views, pages and sections."),
    ("Feedback and status", "Communicating state, progress and outcomes."),
    ("Overlays and floating interfaces", "Content layered above the page."),
    ("Data display", "Presenting records, collections and structured content."),
    ("Data visualization", "Charts and quantitative graphics."),
    ("Layout and composition", "Arranging and separating content."),
    ("Content and media", "Text, icons, images and files."),
]

FAMILY_CATEGORY: dict[str, str] = {
    "Button": "Actions", "Button group": "Actions", "Link": "Actions", "Toolbar": "Actions",
    "Text input": "Forms and input", "Textarea": "Forms and input", "Select": "Forms and input", "Combobox": "Forms and input",
    "Checkbox": "Forms and input", "Radio": "Forms and input", "Switch": "Forms and input", "Slider": "Forms and input",
    "Date & time picker": "Forms and input", "Form": "Forms and input", "Search": "Forms and input", "Color picker": "Forms and input",
    "Rating": "Forms and input", "File upload": "Forms and input",
    "Tabs": "Navigation", "Breadcrumbs": "Navigation", "Pagination": "Navigation", "Menu": "Navigation", "Navigation": "Navigation",
    "Alert": "Feedback and status", "Toast / Notification": "Feedback and status", "Badge": "Feedback and status",
    "Progress": "Feedback and status", "Skeleton": "Feedback and status", "Empty state": "Feedback and status",
    "Dialog": "Overlays and floating interfaces", "Drawer / Sheet": "Overlays and floating interfaces", "Popover": "Overlays and floating interfaces",
    "Tooltip": "Overlays and floating interfaces", "Portal / Overlay utility": "Overlays and floating interfaces",
    "Table / Data grid": "Data display", "List": "Data display", "Tree": "Data display", "Avatar": "Data display", "Card": "Data display",
    "Accordion": "Data display", "Calendar": "Data display", "Timeline": "Data display", "Tag": "Data display", "Carousel": "Data display",
    "Chart": "Data visualization",
    "Layout primitive": "Layout and composition", "Divider": "Layout and composition", "Resizable panels": "Layout and composition",
    "Icon": "Content and media", "Image": "Content and media", "Typography": "Content and media",
}
UNCLASSIFIED = "Other components"


def category_of(family: str | None) -> str:
    return FAMILY_CATEGORY.get(family or "", UNCLASSIFIED)


# ── token categories ─────────────────────────────────────────────────────────────────────────────────────────────────
TOKEN_CATEGORIES = ["color", "typography", "spacing", "sizing", "border", "radius", "shadow", "motion", "breakpoint", "z-index", "opacity", "other"]
_HEX = re.compile(r"^#(?:[0-9a-f]{3,4}|[0-9a-f]{6}|[0-9a-f]{8})$", re.I)
_RULES: list[tuple[str, re.Pattern]] = [
    ("radius", re.compile(r"radius|rounded|corner", re.I)),
    ("shadow", re.compile(r"shadow|elevation", re.I)),
    ("motion", re.compile(r"duration|motion|easing|\bease\b|transition|animation|delay", re.I)),
    ("breakpoint", re.compile(r"breakpoint|screen-?(xs|sm|md|lg|xl)", re.I)),
    ("z-index", re.compile(r"z-?index|zindex|layer", re.I)),
    ("opacity", re.compile(r"opacity|alpha", re.I)),
    ("typography", re.compile(r"font|line-?height|letter-?spacing|typo|text-?size|heading|\bh[1-6]\b", re.I)),
    ("border", re.compile(r"border|outline|stroke|divider", re.I)),
    ("spacing", re.compile(r"spac|padding|margin|gap|gutter|inset", re.I)),
    ("sizing", re.compile(r"size|width|height|dimension", re.I)),
    ("color", re.compile(r"colou?r|bg|background|foreground|fill|tint|palette", re.I)),
]


def token_category(path: str, type_: str | None, group: str | None, value: str | None) -> str:
    t = (type_ or "").lower()
    if t == "color" or (value and (_HEX.match(value.strip()) or re.match(r"^(rgba?|hsla?|oklch|oklab)\(", value.strip(), re.I))):
        return "color"
    if t in ("fontweight", "fontfamily", "typography", "fontsize"):
        return "typography"
    if t == "shadow":
        return "shadow"
    hint = f"{path} {group or ''}"
    for cat, rx in _RULES:
        if rx.search(hint):
            return cat
    return "other"


def token_tier(component: str | None, group: str | None, alias_of: str | None, path: str) -> str:
    """component: scoped to a component (declared, or an Ant-style `Button.xxx` path); semantic: an alias of another
    token; primitive: holds its own value."""
    if component or re.match(r"^[A-Z][A-Za-z]+\.", path):
        return "component"
    return "semantic" if alias_of else "primitive"


# ── slugs ────────────────────────────────────────────────────────────────────────────────────────────────────────────
def slugify(text: str, max_len: int = 80) -> str:
    s = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return (s[:max_len].rstrip("-")) or "item"


def _assign(rows: Iterable[tuple[int, Any, str, str | None]], max_len: int) -> list[tuple[int, str]]:
    """rows: (id, scope, base text, current slug). Returns (id, new slug) for rows without one, unique within scope.
    Rows are processed by id so the oldest record keeps the plain slug."""
    rows = sorted(rows, key=lambda r: r[0])
    taken: dict[Any, set[str]] = defaultdict(set)
    for _, scope, _, slug in rows:
        if slug:
            taken[scope].add(slug)
    out = []
    for rid, scope, text, slug in rows:
        if slug:
            continue
        base = slugify(text, max_len)
        cand, n = base, 2
        while cand in taken[scope]:
            cand, n = f"{base}-{n}", n + 1
        taken[scope].add(cand)
        out.append((rid, cand))
    return out


def _apply(db: Session, model, pairs: list[tuple[int, str]], col: str = "slug") -> int:
    for rid, val in pairs:
        db.execute(update(model).where(model.id == rid).values({col: val}))
    return len(pairs)


def refresh(db: Session) -> dict[str, int]:
    summary: dict[str, int] = {}
    # systems: one global namespace
    summary["system_slugs"] = _apply(db, DesignSystem, _assign(
        ((i, "all", n, s) for i, n, s in db.execute(select(DesignSystem.id, DesignSystem.name, DesignSystem.slug))), 80))
    # components: unique per system (two libraries in one system can both have a "Table")
    summary["component_slugs"] = _apply(db, Component, _assign(
        ((i, sid, n, s) for i, sid, n, s in db.execute(select(Component.id, Component.system_id, Component.name, Component.slug))), 120))
    # tokens: per system; the same path in two themes gets a theme suffix rather than a counter
    rows = list(db.execute(select(DesignToken.id, DesignToken.system_id, DesignToken.path, DesignToken.theme, DesignToken.slug)))
    seen: dict[tuple, int] = defaultdict(int)
    for _, sid, path, _, _ in rows:
        seen[(sid, slugify(path, 180))] += 1
    summary["token_slugs"] = _apply(db, DesignToken, _assign(
        ((i, sid, f"{p}-{th}" if seen[(sid, slugify(p, 180))] > 1 and th and th != "default" else p, s) for i, sid, p, th, s in rows), 200))
    summary["guideline_slugs"] = _apply(db, Guideline, _assign(
        ((i, sid, t, s) for i, sid, t, s in db.execute(select(Guideline.id, Guideline.system_id, Guideline.title, Guideline.slug))), 160))

    changed = 0
    for i, path, typ, group, raw, res, comp, alias, cat, tier in db.execute(select(
            DesignToken.id, DesignToken.path, DesignToken.type, DesignToken.group, DesignToken.raw_value, DesignToken.resolved_value,
            DesignToken.component, DesignToken.alias_of, DesignToken.category, DesignToken.tier)):
        c, t = token_category(path, typ, group, res or raw), token_tier(comp, group, alias, path)
        if (c, t) != (cat, tier):
            db.execute(update(DesignToken).where(DesignToken.id == i).values(category=c, tier=t))
            changed += 1
    summary["token_categories"] = changed

    order = {name: i for i, (name, _) in enumerate(CATEGORIES)}
    for pos, (fam, aliases) in enumerate(COMPONENT_FAMILIES.items()):
        cat = category_of(fam)
        stmt = insert(ComponentFamily).values(name=fam, slug=slugify(fam), category=cat, aliases=aliases, position=order.get(cat, 99) * 100 + pos)
        db.execute(stmt.on_conflict_do_update(index_elements=["name"], set_={"category": cat, "aliases": aliases, "position": order.get(cat, 99) * 100 + pos}))
    summary["families"] = len(COMPONENT_FAMILIES)
    return summary


def resolve_system(db: Session, ref: str | int) -> DesignSystem | None:
    """A system by numeric id or slug."""
    ref = str(ref)
    if ref.isdigit():
        return db.get(DesignSystem, int(ref))
    return db.scalar(select(DesignSystem).where(DesignSystem.slug == ref))
