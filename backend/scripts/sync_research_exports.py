from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import json
import csv
from datetime import datetime, timezone
from sqlalchemy import select
from app.database.session import session_scope
from app.models import DesignSystem, Component, DesignToken, Guideline, Source, Report

out_dir = Path(__file__).resolve().parents[2] / "research" / "output"

def ser(v):
    if isinstance(v, datetime):
        return v.isoformat()
    return v

with session_scope() as db:
    # 1. design_systems.json & design_systems.csv
    systems = db.scalars(select(DesignSystem).order_by(DesignSystem.source_count.desc(), DesignSystem.name)).all()
    sys_list = []
    sys_csv_rows = []
    for s in systems:
        d = {
            "system_id": s.key,
            "name": s.name,
            "organization": s.organization,
            "documentation_url": s.documentation_url,
            "official_docs_url": s.official_docs_url,
            "repository_url": s.repository_url,
            "storybook_url": s.storybook_url,
            "design_resource_url": s.design_resource_url,
            "supported_frameworks": s.frameworks,
            "supported_platforms": s.platforms,
            "styling_strategy": s.styling_strategy,
            "token_architecture": s.token_architecture,
            "accessibility_documentation": s.accessibility_documentation,
            "governance_documentation": s.governance,
            "ai_readiness": s.ai_readiness,
            "source_count": s.source_count,
            "sources": s.source_keys,
            "verification_status": s.verification_status,
            "verification_basis": s.verification_basis,
            "verification_coverage": s.verification_coverage,
            "component_count": s.component_count,
            "token_count": s.token_count,
            "attributes": s.attributes,
            "last_verified_at": s.last_verified_at.isoformat() if s.last_verified_at else None
        }
        sys_list.append(d)
        sys_csv_rows.append({
            "system_id": s.key,
            "name": s.name,
            "organization": s.organization,
            "documentation_url": s.documentation_url,
            "repository_url": s.repository_url,
            "storybook_url": s.storybook_url,
            "source_count": s.source_count,
            "component_count": s.component_count,
            "token_count": s.token_count,
            "verification_status": s.verification_status,
            "frameworks": "; ".join(s.frameworks or [])
        })
    (out_dir / "design_systems.json").write_text(json.dumps(sys_list, indent=2, ensure_ascii=False))
    print(f"Wrote design_systems.json ({len(sys_list)} systems)")
    
    with open(out_dir / "design_systems.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(sys_csv_rows[0].keys()))
        writer.writeheader()
        writer.writerows(sys_csv_rows)
    print("Wrote design_systems.csv")

    # 2. components.jsonl & components.csv
    components = db.scalars(select(Component).order_by(Component.library, Component.name)).all()
    comp_csv_rows = []
    with open(out_dir / "components.jsonl", "w", encoding="utf-8") as f:
        for c in components:
            cd = {
                "id": c.id,
                "name": c.name,
                "family": c.family,
                "library": c.library,
                "system_id": c.system_id,
                "detail_level": c.detail_level,
                "kind": c.kind,
                "description": c.description,
                "documentation_url": c.documentation_url,
                "props_count": c.props_count,
                "keyboard_count": c.keyboard_count,
                "a11y_count": c.a11y_count,
                "verification_status": c.verification_status,
                "source_version": c.source_version
            }
            f.write(json.dumps(cd, ensure_ascii=False) + "\n")
            comp_csv_rows.append(cd)
    print(f"Wrote components.jsonl ({len(components)} components)")
    
    with open(out_dir / "components.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(comp_csv_rows[0].keys()))
        writer.writeheader()
        writer.writerows(comp_csv_rows)
    print("Wrote components.csv")

    # 3. sources.json & sources.csv
    sources = db.scalars(select(Source).order_by(Source.key)).all()
    src_list = []
    for s in sources:
        src_list.append({
            "id": s.id,
            "key": s.key,
            "name": s.name,
            "url": s.url,
            "domain": s.domain,
            "source_type": s.source_type,
            "origin": s.origin,
            "status": s.status,
            "http_status": s.http_status,
            "pages_attempted": s.pages_attempted,
            "pages_ok": s.pages_ok,
            "records_count": s.records_count,
            "error_count": s.error_count,
            "last_attempted_at": s.last_attempted_at.isoformat() if s.last_attempted_at else None,
            "last_success_at": s.last_success_at.isoformat() if s.last_success_at else None
        })
    (out_dir / "sources.json").write_text(json.dumps(src_list, indent=2, ensure_ascii=False))
    print(f"Wrote sources.json ({len(src_list)} sources)")
    
    with open(out_dir / "sources.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(src_list[0].keys()))
        writer.writeheader()
        writer.writerows(src_list)
    print("Wrote sources.csv")

    # 4. Reports (research_report.md, knowledge_base_index.md)
    for r in db.scalars(select(Report).order_by(Report.created_at.desc())).all():
        if r.kind == "research_report" and r.content_md:
            (out_dir / "research_report.md").write_text(r.content_md)
        elif r.kind == "knowledge_base_index" and r.content_md:
            (out_dir / "knowledge_base_index.md").write_text(r.content_md)
        elif r.kind == "comparison_report" and r.content_md:
            (out_dir / "design_system_comparison.md").write_text(r.content_md)
    print("Synced markdown reports")
