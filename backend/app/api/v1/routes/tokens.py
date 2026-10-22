from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from ....core.exceptions import NotFound
from ....database.session import get_db
from ....models import DesignToken, Evidence, Record, Source, TokenReference
from ....repositories import list_tokens, token_facets
from ....schemas import Item, Page, TokenOut
from ...deps import PageParams, page_params, require
from ..common import ERRORS, csv_list, page_out
from ..serializers import token_out

router = APIRouter(prefix="/tokens", tags=["tokens"], responses=ERRORS, dependencies=[Depends(require("public:read"))])


@router.get("", response_model=Page[TokenOut])
def list_(q: str | None = Query(None, max_length=200), type_: list[str] | None = Depends(csv_list("type")), theme: list[str] | None = Depends(csv_list("theme")),
          platform: list[str] | None = Depends(csv_list("platform")), group: list[str] | None = Depends(csv_list("group")),
          system: list[str] | None = Depends(csv_list("system")), source: list[str] | None = Depends(csv_list("source")),
          component: list[str] | None = Depends(csv_list("component")), has_alias: bool | None = None, sort: str | None = Query(None, max_length=30),
          pp: PageParams = Depends(page_params), db: Session = Depends(get_db)):
    rows, total = list_tokens(db, q=q, type_=type_, theme=theme, platform=platform, group=group, system=system, source_key=source, component=component,
                              has_alias=has_alias, sort=sort, page=pp.page, page_size=pp.page_size)
    return page_out([token_out(t, k) for t, k in rows], total, pp.page, pp.page_size)


@router.get("/facets")
def facets(db: Session = Depends(get_db)):
    return {"data": token_facets(db)}


def _get(db: Session, token_id: int):
    row = db.execute(select(DesignToken, Source.key, Record).join(Source, Source.id == DesignToken.source_id).join(Record, Record.id == DesignToken.record_id)
                     .where(DesignToken.id == token_id)).first()
    if not row:
        raise NotFound("Token not found.")
    return row


@router.get("/{token_id}")
def get(token_id: int, db: Session = Depends(get_db)):
    t, key, rec = _get(db, token_id)
    ev = db.scalars(select(Evidence).where(Evidence.record_id == rec.id).limit(10)).all()
    d = token_out(t, key)
    d.update(record_key=rec.record_key, source_url=rec.source_url, source_section=(rec.extra or {}).get("source_section"),
             evidence=[{"url": e.url, "excerpt": e.excerpt, "source_version": e.source_version, "raw_document_id": e.raw_document_id} for e in ev],
             value_note=("raw_value is the source value; resolved_value is computed by following documented aliases within the same source."
                         + (" Type was inferred from the name/value (not source-declared)." if t.type_inferred else "")),
             extra=rec.content)
    return {"data": d}


@router.get("/{token_id}/references", response_model=Page[TokenOut], summary="Tokens this token aliases")
def references(token_id: int, db: Session = Depends(get_db)):
    _get(db, token_id)
    T = aliased(DesignToken)
    rows = db.execute(select(T, Source.key).join(TokenReference, TokenReference.references_token_id == T.id).join(Source, Source.id == T.source_id)
                      .where(TokenReference.token_id == token_id).limit(50)).all()
    return page_out([token_out(t, k) for t, k in rows], len(rows), 1, 50)


@router.get("/{token_id}/dependents", response_model=Page[TokenOut], summary="Tokens that alias this token")
def dependents(token_id: int, pp: PageParams = Depends(page_params), db: Session = Depends(get_db)):
    _get(db, token_id)
    T = aliased(DesignToken)
    from ....repositories import paginate
    stmt = (select(T, Source.key).join(TokenReference, TokenReference.token_id == T.id).join(Source, Source.id == T.source_id)
            .where(TokenReference.references_token_id == token_id).order_by(T.path))
    rows, total = paginate(db, stmt, pp.page, pp.page_size)
    return page_out([token_out(t, k) for t, k in rows], total, pp.page, pp.page_size)
