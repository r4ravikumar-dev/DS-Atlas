"""Storybook projects, stories and variants (read) + extraction job (researcher)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ....core.exceptions import NotFound
from ....database.session import get_db
from ....models import StorybookProject, StorybookStory, StorybookVariant
from ....repositories import paginate
from ....services import jobs as jobsvc
from ....services.audit import audit
from ...deps import PageParams, Principal, page_params, require
from ..common import ERRORS, csv_list, page_out

router = APIRouter(prefix="/storybook", tags=["storybook"], responses=ERRORS)
P_FIELDS = ("id", "slug", "title", "organization", "storybook_url", "resolved_url", "repository_url", "framework", "storybook_version", "system_key", "status",
            "index_kind", "stories_discovered", "stories_extracted", "docs_entries", "variants_extracted", "source_files_parsed", "failed_requests",
            "limitation", "retry_eligible", "raw_index_document_id", "last_checked_at")
S_FIELDS = ("id", "project_id", "entry_id", "entry_type", "title", "name", "export_name", "component_name", "component_id", "resolution_status", "tags",
            "import_path", "story_url", "args", "arg_types", "source_file_url", "extraction_status", "evidence", "last_verified_at")
V_FIELDS = ("id", "story_id", "project_id", "component_id", "component_name", "label", "props", "method", "confidence", "evidence")


def _d(o, fields):
    return {f: getattr(o, f) for f in fields}


@router.post("/crawl", status_code=status.HTTP_202_ACCEPTED, summary="Queue showcase enumeration + story extraction")
def crawl(refresh: bool = False, p: Principal = Depends(require("crawl:start")), db: Session = Depends(get_db)):
    job = jobsvc.enqueue(db, "storybook", params={"refresh": refresh}, created_by=p.id, priority=110)
    audit(db, p.id, "storybook.crawl", "job", job.id)
    db.commit()
    return {"data": {"job_ids": [job.id]}}


def _system_projects(db: Session, system_id: int):
    from ....models import DesignSystem
    return select(StorybookProject.id).join(DesignSystem, DesignSystem.key == StorybookProject.system_key).where(DesignSystem.id == system_id)


@router.get("/projects", dependencies=[Depends(require("read"))])
def projects(q: str | None = Query(None, max_length=200), status_: str | None = Query(None, alias="status"), sort: str = Query("title", pattern="^-?(title|stories|variants)$"),
             pp: PageParams = Depends(page_params), db: Session = Depends(get_db)):
    stmt = select(StorybookProject)
    if q:
        stmt = stmt.where(or_(StorybookProject.title.ilike(f"%{q}%"), StorybookProject.organization.ilike(f"%{q}%"), StorybookProject.slug.ilike(f"%{q}%")))
    if status_:
        stmt = stmt.where(StorybookProject.status == status_)
    col = {"title": StorybookProject.title, "stories": StorybookProject.stories_extracted, "variants": StorybookProject.variants_extracted}[sort.lstrip("-")]
    stmt = stmt.order_by(col.desc() if sort.startswith("-") else col.asc(), StorybookProject.id)
    rows, total = paginate(db, stmt, pp.page, pp.page_size)
    return page_out([_d(r, P_FIELDS) for (r,) in rows], total, pp.page, pp.page_size)


@router.get("/projects/{project_id}", dependencies=[Depends(require("read"))])
def project(project_id: int, db: Session = Depends(get_db)):
    p = db.get(StorybookProject, project_id)
    if not p:
        raise NotFound("Storybook project not found.")
    return {"data": _d(p, P_FIELDS)}


@router.get("/stories", dependencies=[Depends(require("read"))])
def stories(project_id: int | None = None, system_id: int | None = None, q: str | None = Query(None, max_length=200), entry_type: list[str] | None = Depends(csv_list("entry_type")),
            resolution: str | None = Query(None, pattern="^(linked|unresolved|not_applicable)$"), component_id: int | None = None,
            has_args: bool | None = None, pp: PageParams = Depends(page_params), db: Session = Depends(get_db)):
    stmt = select(StorybookStory)
    if project_id:
        stmt = stmt.where(StorybookStory.project_id == project_id)
    if system_id:
        stmt = stmt.where(StorybookStory.project_id.in_(_system_projects(db, system_id)))
    if component_id:
        stmt = stmt.where(StorybookStory.component_id == component_id)
    if q:
        stmt = stmt.where(or_(StorybookStory.title.ilike(f"%{q}%"), StorybookStory.name.ilike(f"%{q}%")))
    if entry_type:
        stmt = stmt.where(StorybookStory.entry_type.in_(entry_type))
    if resolution:
        stmt = stmt.where(StorybookStory.resolution_status == resolution)
    if has_args:
        stmt = stmt.where(StorybookStory.args.is_not(None))
    rows, total = paginate(db, stmt.order_by(StorybookStory.title, StorybookStory.name, StorybookStory.id), pp.page, pp.page_size)
    return page_out([_d(r, S_FIELDS) for (r,) in rows], total, pp.page, pp.page_size)


@router.get("/stories/{story_id}", dependencies=[Depends(require("read"))])
def story(story_id: int, db: Session = Depends(get_db)):
    s = db.get(StorybookStory, story_id)
    if not s:
        raise NotFound("Story not found.")
    vs = db.scalars(select(StorybookVariant).where(StorybookVariant.story_id == s.id).limit(100)).all()
    return {"data": {**_d(s, S_FIELDS), "variants": [_d(v, V_FIELDS) for v in vs]}}


@router.get("/variants", dependencies=[Depends(require("read"))])
def variants(project_id: int | None = None, system_id: int | None = None, component_id: int | None = None, method: list[str] | None = Depends(csv_list("method")),
             q: str | None = Query(None, max_length=200), pp: PageParams = Depends(page_params), db: Session = Depends(get_db)):
    stmt = select(StorybookVariant)
    if project_id:
        stmt = stmt.where(StorybookVariant.project_id == project_id)
    if system_id:
        stmt = stmt.where(StorybookVariant.project_id.in_(_system_projects(db, system_id)))
    if component_id:
        stmt = stmt.where(StorybookVariant.component_id == component_id)
    if method:
        stmt = stmt.where(StorybookVariant.method.in_(method))
    if q:
        stmt = stmt.where(or_(StorybookVariant.label.ilike(f"%{q}%"), StorybookVariant.component_name.ilike(f"%{q}%")))
    rows, total = paginate(db, stmt.order_by(StorybookVariant.component_name, StorybookVariant.id), pp.page, pp.page_size)
    return page_out([_d(r, V_FIELDS) for (r,) in rows], total, pp.page, pp.page_size)
