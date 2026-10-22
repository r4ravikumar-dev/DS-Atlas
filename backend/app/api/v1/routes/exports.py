from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ....core.exceptions import AppError, Forbidden, NotFound, Unauthorized
from ....core.permissions import has_permission
from ....core.security import create_download_token, decode_download_token
from ....database.session import get_db
from ....models import Job, User
from ....repositories import list_jobs
from ....schemas import DownloadLink, ExportCreate, ExportJobOut, Item, JobAccepted, Page
from ....services import jobs as jobsvc
from ....services import settings_service
from ....services.audit import audit
from ....services.storage import storage
from ...deps import PageParams, Principal, page_params, require
from ..common import ERRORS, page_out

router = APIRouter(prefix="/export-jobs", tags=["exports"], responses=ERRORS)


def _get(db: Session, job_id: uuid.UUID) -> Job:
    j = db.get(Job, job_id)
    if not j or j.kind != "export":
        raise NotFound("Export job not found.")
    return j


@router.get("", response_model=Page[ExportJobOut], dependencies=[Depends(require("export:create"))])
def list_(pp: PageParams = Depends(page_params), db: Session = Depends(get_db)):
    items, total = list_jobs(db, kinds=["export"], page=pp.page, page_size=pp.page_size)
    return page_out(items, total, pp.page, pp.page_size)


@router.post("", response_model=Item[JobAccepted], status_code=status.HTTP_202_ACCEPTED, summary="Request an asynchronous export")
def create(body: ExportCreate, p: Principal = Depends(require("export:create")), db: Session = Depends(get_db)):
    policy = settings_service.get_config(db)["export_policy"]
    if body.format not in policy.get("formats", []):
        raise AppError(f"Format '{body.format}' is disabled by export policy.", code="EXPORT_FORMAT_DISABLED", status_code=422)
    if not has_permission(p.role, "read") or (policy.get("min_role") == "admin" and p.role != "admin"):
        raise Forbidden("Export policy does not allow your role.")
    job = jobsvc.enqueue(db, "export", params={"format": body.format, "resource": body.resource}, created_by=p.id, priority=50)
    audit(db, p.id, "export.request", "job", job.id, format=body.format, resource=body.resource)
    db.commit()
    return {"data": {"job_ids": [job.id]}}


@router.get("/{export_job_id}", response_model=Item[ExportJobOut], dependencies=[Depends(require("export:create"))])
def get(export_job_id: uuid.UUID, db: Session = Depends(get_db)):
    return {"data": _get(db, export_job_id)}


@router.post("/{export_job_id}/download-link", response_model=Item[DownloadLink], summary="Issue a short-lived signed download URL")
def link(export_job_id: uuid.UUID, p: Principal = Depends(require("export:create")), db: Session = Depends(get_db)):
    j = _get(db, export_job_id)
    if j.status != "succeeded":
        raise AppError("Export is not ready.", code="EXPORT_NOT_READY", status_code=409)
    token = create_download_token(str(j.id), str(p.id))
    return {"data": {"url": f"/api/v1/export-jobs/{j.id}/download?token={token}", "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10)}}


@router.get("/{export_job_id}/download", summary="Download a generated export (session or signed token)")
def download(export_job_id: uuid.UUID, request: Request, token: str | None = Query(None, max_length=2000), db: Session = Depends(get_db)):
    from ...deps import get_principal
    # Authorize before looking the job up, so unauthenticated callers cannot probe which export IDs exist.
    user_id = None
    if token:
        data = decode_download_token(token)
        if not data or data.get("job") != str(export_job_id):
            raise Unauthorized("Invalid or expired download token.")
        user_id = data["sub"]
    else:
        p = get_principal(request, db)
        if p.user is None or not has_permission(p.role, "export:create"):
            raise Unauthorized("Authentication required.")
        user_id = str(p.id)
    u = db.get(User, uuid.UUID(user_id))
    if not u or not u.is_active or not has_permission(u.role, "export:create"):
        raise Forbidden("Not allowed.")
    j = _get(db, export_job_id)
    res = j.result or {}
    if j.status != "succeeded" or not res.get("storage_key"):
        raise AppError("Export is not ready.", code="EXPORT_NOT_READY", status_code=409)
    if res.get("expires_at") and datetime.fromisoformat(res["expires_at"]) < datetime.now(timezone.utc):
        raise AppError("Export has expired; request a new one.", code="EXPORT_EXPIRED", status_code=410)
    if not storage().exists(res["storage_key"]):
        raise NotFound("Export file is no longer available.")
    audit(db, u.id, "export.download", "job", j.id)
    db.commit()
    return FileResponse(storage().path(res["storage_key"]), filename=res["filename"], media_type="application/octet-stream",
                        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})
