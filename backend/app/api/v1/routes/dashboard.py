from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ....database.session import get_db
from ....schemas import DashboardSummary, Item
from ....services import dashboard, jobs as jobsvc
from ...deps import require
from ..common import ERRORS

router = APIRouter(prefix="/dashboard", tags=["dashboard"], responses=ERRORS, dependencies=[Depends(require("read"))])


@router.get("/summary", response_model=Item[DashboardSummary])
def summary(db: Session = Depends(get_db)):
    return {"data": dashboard.summary(db)}


@router.get("/activity")
def activity(days: int = Query(30, ge=1, le=365), limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    a = dashboard.activity(db, days, limit)
    return {"data": {"jobs": [jobsvc.to_out(j) for j in a["jobs"]], "recent_records": a["recent_records"], "jobs_per_day": a["jobs_per_day"]}}


@router.get("/source-coverage")
def source_coverage(db: Session = Depends(get_db)):
    return {"data": dashboard.source_coverage(db)}


@router.get("/category-distribution")
def category_distribution(db: Session = Depends(get_db)):
    return {"data": dashboard.category_distribution(db)}
