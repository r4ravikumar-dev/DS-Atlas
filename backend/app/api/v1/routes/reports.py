from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ....core.exceptions import NotFound
from ....database.session import get_db
from ....models import Report
from ....repositories import paginate
from ....schemas import Item, Page, ReportDetail, ReportOut
from ...deps import PageParams, page_params, require
from ..common import ERRORS, page_out

router = APIRouter(prefix="/reports", tags=["reports"], responses=ERRORS, dependencies=[Depends(require("read"))])


@router.get("", response_model=Page[ReportOut])
def list_(kind: str | None = Query(None, max_length=40), latest: bool = Query(True, description="Only the newest report of each kind"),
          pp: PageParams = Depends(page_params), db: Session = Depends(get_db)):
    stmt = select(Report)
    if kind:
        stmt = stmt.where(Report.kind == kind)
    if latest:
        stmt = stmt.distinct(Report.kind).order_by(Report.kind, Report.created_at.desc())
    else:
        stmt = stmt.order_by(Report.created_at.desc())
    rows, total = paginate(db, stmt, pp.page, pp.page_size)
    return page_out([r[0] for r in rows], total, pp.page, pp.page_size)


@router.get("/{report_id}", response_model=Item[ReportDetail])
def get(report_id: uuid.UUID, db: Session = Depends(get_db)):
    r = db.get(Report, report_id)
    if not r:
        raise NotFound("Report not found.")
    return {"data": r}
