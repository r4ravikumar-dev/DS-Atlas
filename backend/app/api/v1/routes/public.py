"""Public, read-only extras for the directory: headline stats and on-the-fly comparisons (nothing is persisted)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ....core.exceptions import AppError
from ....database.session import get_db
from ....models import Component, DesignSystem, DesignToken, Guideline, StorybookProject, StorybookStory, StorybookVariant, SyncRun, SystemResource
from ....services import comparisons as cmp
from ...deps import require
from ..common import ERRORS

router = APIRouter(tags=["public"], responses=ERRORS, dependencies=[Depends(require("public:read"))])


@router.get("/stats", summary="Headline counts of the published dataset")
def stats(db: Session = Depends(get_db)):
    c = lambda m, *w: db.scalar(select(func.count()).select_from(m).where(*w)) or 0  # noqa: E731
    last = db.scalar(select(SyncRun.finished_at).where(SyncRun.status.in_(("succeeded", "partially_succeeded"))).order_by(SyncRun.finished_at.desc()).limit(1))
    return {"data": {
        "design_systems": c(DesignSystem), "components": c(Component), "tokens": c(DesignToken),
        "guidelines": c(Guideline, Guideline.record_type.in_(("guideline", "specification"))), "patterns": c(Guideline, Guideline.record_type == "pattern"),
        "storybook_projects": c(StorybookProject), "stories": c(StorybookStory), "variants": c(StorybookVariant),
        "systems_with_github": db.scalar(select(func.count(func.distinct(SystemResource.system_id))).where(
            SystemResource.resource_type == "github_repository", SystemResource.verification_status != "invalid")) or 0,
        "systems_with_figma": db.scalar(select(func.count(func.distinct(SystemResource.system_id))).where(
            SystemResource.resource_type == "figma_file", SystemResource.verification_status != "invalid")) or 0,
        "content_updated_at": db.scalar(select(func.max(DesignSystem.content_updated_at))),
        "last_sync_at": last,
    }}


@router.get("/compare", summary="Compare 2–6 systems or components from stored records (read-only)")
def compare(kind: str = Query(..., pattern="^(systems|components)$"), ids: str = Query(..., max_length=200),
            dimensions: str | None = Query(None, max_length=300), db: Session = Depends(get_db)):
    try:
        id_list = list(dict.fromkeys(int(x) for x in ids.split(",") if x.strip()))
    except ValueError:
        raise AppError("ids must be comma-separated integers.", code="VALIDATION_ERROR", status_code=422) from None
    if not 2 <= len(id_list) <= 6:
        raise AppError("Compare between 2 and 6 items.", code="VALIDATION_ERROR", status_code=422)
    dims = [d for d in (dimensions or "").split(",") if d] or None
    return {"data": cmp.compute(db, kind, id_list, dims)}
