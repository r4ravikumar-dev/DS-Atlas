"""Export generation (runs in workers). Files are written to object storage under exports/<job_id>/
and served only through the authorized, time-limited download endpoint."""
from __future__ import annotations

import csv
import io
import json
import tempfile
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.config import get_settings
from ..models import Component, DesignSystem, DesignToken, Guideline, Record, Report, Source
from .storage import storage

RESOURCES = ("systems", "components", "tokens", "guidelines", "sources")


def _rows(db: Session, resource: str, max_rows: int) -> list[dict[str, Any]]:
    if resource == "systems":
        q = select(DesignSystem).order_by(DesignSystem.source_count.desc(), DesignSystem.name)
        cols = ["id", "key", "name", "organization", "description", "documentation_url", "repository_url", "storybook_url", "frameworks",
                "styling_strategy", "token_architecture", "accessibility_documentation", "source_count", "source_keys", "verification_status", "last_verified_at"]
    elif resource == "components":
        q = select(Component).order_by(Component.library, Component.name)
        cols = ["id", "name", "family", "library", "system_id", "detail_level", "kind", "description", "documentation_url", "props_count",
                "keyboard_count", "a11y_count", "verification_status", "source_version"]
    elif resource == "tokens":
        q = select(DesignToken).order_by(DesignToken.design_system_name, DesignToken.path)
        cols = ["id", "name", "path", "group", "type", "type_inferred", "raw_value", "resolved_value", "alias_of", "theme", "platform",
                "component", "description", "source_format", "design_system_name", "verification_status", "source_version"]
    elif resource == "guidelines":
        q = select(Guideline).order_by(Guideline.category, Guideline.title)
        cols = ["id", "record_type", "kind", "title", "category", "summary", "section", "priority", "design_system_name", "confidence", "verification_status", "review_status"]
    else:
        q = select(Source).order_by(Source.key)
        cols = ["id", "key", "name", "url", "domain", "source_type", "origin", "status", "http_status", "pages_attempted", "pages_ok",
                "records_count", "error_count", "last_attempted_at", "last_success_at"]
    out = []
    for obj in db.scalars(q.limit(max_rows)):
        d = {c: getattr(obj, c) for c in cols}
        if hasattr(obj, "record_id"):
            rec = db.get(Record, obj.record_id)
            d["source_url"] = rec.source_url if rec else None
        out.append(d)
    return out


def _ser(v: Any) -> Any:
    if isinstance(v, datetime):
        return v.isoformat()
    return v


def _csv(rows: list[dict[str, Any]]) -> bytes:
    buf = io.StringIO()
    if rows:
        w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else _ser(v) for k, v in r.items()})
    return buf.getvalue().encode()


def _xlsx(sheets: dict[str, list[dict[str, Any]]]) -> bytes:
    from openpyxl import Workbook
    wb = Workbook()
    wb.remove(wb.active)
    for name, rows in sheets.items():
        ws = wb.create_sheet(name[:31])
        if rows:
            ws.append(list(rows[0].keys()))
            for r in rows:
                ws.append([json.dumps(v, ensure_ascii=False)[:32000] if isinstance(v, (list, dict)) else _ser(v) for v in r.values()])
    b = io.BytesIO()
    wb.save(b)
    return b.getvalue()


def generate(db: Session, job_id, fmt: str, resource: str, max_rows: int = 250000) -> dict[str, Any]:
    res = list(RESOURCES) if resource == "all" else [resource]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if fmt == "markdown":
        reps = {r.kind: r for r in db.scalars(select(Report).order_by(Report.created_at.desc())) if r.kind in ("research_report", "comparison_report", "knowledge_base_index")}
        parts = [reps[k].content_md for k in ("research_report", "comparison_report", "knowledge_base_index") if k in reps]
        if not parts:
            raise ValueError("No generated reports yet — run a knowledge-base build first.")
        data, filename, rows = "\n\n---\n\n".join(parts).encode(), f"dsrp-reports-{stamp}.md", len(parts)
    else:
        sheets = {r: _rows(db, r, max_rows) for r in res}
        rows = sum(len(v) for v in sheets.values())
        if fmt == "xlsx":
            data, filename = _xlsx(sheets), f"dsrp-{resource}-{stamp}.xlsx"
        elif fmt == "json":
            data = json.dumps({k: v for k, v in sheets.items()} if resource == "all" else sheets[resource], ensure_ascii=False, default=_ser, indent=1).encode()
            filename = f"dsrp-{resource}-{stamp}.json"
        elif fmt == "jsonl":
            lines = (json.dumps({"resource": k, **row}, ensure_ascii=False, default=_ser) for k, v in sheets.items() for row in v)
            data, filename = ("\n".join(lines) + "\n").encode(), f"dsrp-{resource}-{stamp}.jsonl"
        elif fmt == "csv" and len(sheets) == 1:
            data, filename = _csv(next(iter(sheets.values()))), f"dsrp-{resource}-{stamp}.csv"
        else:  # csv for several resources, or a full bundle → zip
            b = io.BytesIO()
            with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as z:
                for k, v in sheets.items():
                    z.writestr(f"{k}.csv", _csv(v))
                    if fmt == "bundle":
                        z.writestr(f"{k}.jsonl", "\n".join(json.dumps(r, ensure_ascii=False, default=_ser) for r in v) + "\n")
                if fmt == "bundle":
                    for r in db.scalars(select(Report).order_by(Report.created_at.desc())):
                        name = f"reports/{r.kind}.md"
                        if name not in z.namelist():
                            z.writestr(name, r.content_md)
                    z.writestr("design_systems_catalog.xlsx", _xlsx(sheets))
            data, filename = b.getvalue(), f"dsrp-{resource}-{fmt}-{stamp}.zip"
    key = storage().put(f"exports/{job_id}/{filename}", data)
    expires = datetime.now(timezone.utc) + timedelta(hours=get_settings().export_ttl_hours)
    return {"storage_key": key, "filename": filename, "size_bytes": len(data), "row_count": rows, "format": fmt, "resource": resource,
            "expires_at": expires.isoformat()}
