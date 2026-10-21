from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ....core.exceptions import NotFound
from ....database.session import get_db
from ....models import Comparison
from ....repositories import paginate
from ....schemas import ComparisonCreate, ComparisonOut, ComparisonUpdate, Item, Page
from ....services import comparisons as cmp
from ....services.audit import audit
from ...deps import PageParams, Principal, page_params, require
from ..common import ERRORS, page_out

router = APIRouter(prefix="/comparisons", tags=["comparisons"], responses=ERRORS)


def _get(db: Session, cid: uuid.UUID) -> Comparison:
    c = db.get(Comparison, cid)
    if not c:
        raise NotFound("Comparison not found.")
    return c


@router.get("/dimensions", dependencies=[Depends(require("read"))])
def dimensions():
    return {"data": {"systems": cmp.SYSTEM_DIMENSIONS, "components": cmp.COMPONENT_DIMENSIONS}}


@router.get("", response_model=Page[ComparisonOut], dependencies=[Depends(require("read"))])
def list_(pp: PageParams = Depends(page_params), db: Session = Depends(get_db)):
    rows, total = paginate(db, select(Comparison).order_by(Comparison.updated_at.desc()), pp.page, pp.page_size)
    return page_out([r[0] for r in rows], total, pp.page, pp.page_size)


@router.post("", response_model=Item[ComparisonOut], status_code=status.HTTP_201_CREATED, summary="Create and generate a comparison")
def create(body: ComparisonCreate, p: Principal = Depends(require("comparison:write")), db: Session = Depends(get_db)):
    c = Comparison(name=body.name, kind=body.kind, item_ids=body.item_ids, dimensions=body.dimensions, created_by=p.id)
    db.add(c)
    db.flush()
    cmp.generate(db, c)
    audit(db, p.id, "comparison.create", "comparison", c.id)
    db.commit()
    return {"data": c}


@router.get("/{comparison_id}", response_model=Item[ComparisonOut], dependencies=[Depends(require("read"))])
def get(comparison_id: uuid.UUID, db: Session = Depends(get_db)):
    return {"data": _get(db, comparison_id)}


@router.patch("/{comparison_id}", response_model=Item[ComparisonOut])
def update(comparison_id: uuid.UUID, body: ComparisonUpdate, p: Principal = Depends(require("comparison:write")), db: Session = Depends(get_db)):
    c = _get(db, comparison_id)
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(c, k, v)
    c.status = "draft"
    db.commit()
    return {"data": c}


@router.post("/{comparison_id}/generate", response_model=Item[ComparisonOut], summary="(Re)generate from current records (synchronous; ≤ 6 items)")
def generate(comparison_id: uuid.UUID, p: Principal = Depends(require("comparison:write")), db: Session = Depends(get_db)):
    c = cmp.generate(db, _get(db, comparison_id))
    db.commit()
    return {"data": c}


@router.delete("/{comparison_id}", status_code=204)
def delete(comparison_id: uuid.UUID, p: Principal = Depends(require("comparison:write")), db: Session = Depends(get_db)):
    db.delete(_get(db, comparison_id))
    audit(db, p.id, "comparison.delete", "comparison", comparison_id)
    db.commit()
