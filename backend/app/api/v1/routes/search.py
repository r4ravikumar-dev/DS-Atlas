from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ....database.session import get_db
from ....schemas import Page, SearchHit
from ....search import ALL_TYPES, search
from ...deps import PageParams, page_params, require
from ..common import ERRORS, csv_list, page_out

router = APIRouter(tags=["search"], responses=ERRORS)


@router.get("/search", response_model=Page[SearchHit], dependencies=[Depends(require("search"))],
            summary="Global full-text search across systems, sources, components, tokens, guidelines, patterns and resources")
def global_search(q: str = Query(..., min_length=1, max_length=200), type_: list[str] | None = Depends(csv_list("type", f"One of: {', '.join(ALL_TYPES)}")),
                  category: list[str] | None = Depends(csv_list("category")), source: list[str] | None = Depends(csv_list("source")),
                  technology: list[str] | None = Depends(csv_list("technology")), pp: PageParams = Depends(page_params), db: Session = Depends(get_db)):
    types = [t for t in (type_ or []) if t in ALL_TYPES] or None
    hits, total, facets = search(db, q, types=types, category=category, source=source, technology=technology, page=pp.page, page_size=pp.page_size)
    return page_out(hits, total, pp.page, pp.page_size, {"facets": facets})
