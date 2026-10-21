from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ....core.exceptions import NotFound
from ....database.session import get_db
from ....models import DiscoveredUrl, Evidence, RawDocument, Record, Source
from ....services.storage import storage
from ...deps import require
from ..common import ERRORS

router = APIRouter(tags=["documents"], responses=ERRORS, dependencies=[Depends(require("read"))])


@router.get("/documents/{document_id}", summary="Raw document snapshot metadata")
def document(document_id: int, db: Session = Depends(get_db)):
    d = db.get(RawDocument, document_id)
    if not d:
        raise NotFound("Document not found.")
    urls = db.execute(select(DiscoveredUrl.url, Source.key).join(Source, Source.id == DiscoveredUrl.source_id)
                      .where(DiscoveredUrl.raw_document_id == d.id).limit(20)).all()
    return {"data": {"id": d.id, "content_sha256": d.content_sha256, "content_type": d.content_type, "size_bytes": d.size_bytes, "first_url": d.first_url,
                     "fetched_at": d.fetched_at, "urls": [{"url": u, "source_key": k} for u, k in urls]}}


@router.get("/documents/{document_id}/content", summary="Download the stored snapshot (served as an inert attachment)")
def document_content(document_id: int, db: Session = Depends(get_db)):
    d = db.get(RawDocument, document_id)
    if not d or not storage().exists(d.storage_key):
        raise NotFound("Document not found.")
    # Untrusted content: never render inline as HTML in our origin.
    return FileResponse(storage().path(d.storage_key), media_type="text/plain; charset=utf-8", filename=f"snapshot-{d.content_sha256[:12]}.txt",
                        headers={"Content-Security-Policy": "sandbox; default-src 'none'", "X-Content-Type-Options": "nosniff"})


@router.get("/records/{record_id}", summary="Any extracted record with evidence")
def record(record_id: int, db: Session = Depends(get_db)):
    row = db.execute(select(Record, Source.key, Source.name).join(Source, Source.id == Record.source_id).where(Record.id == record_id)).first()
    if not row:
        raise NotFound("Record not found.")
    r, key, name = row
    ev = db.scalars(select(Evidence).where(Evidence.record_id == r.id).limit(20)).all()
    return {"data": {"id": r.id, "record_key": r.record_key, "record_type": r.record_type, "title": r.title, "summary": r.summary,
                     "primary_category": r.primary_category, "secondary_categories": r.secondary_categories, "tags": r.tags, "organization": r.organization,
                     "design_system_name": r.design_system_name, "system_id": r.system_id, "source_id": r.source_id, "source_key": key, "source_name": name,
                     "source_url": r.source_url, "source_version": r.source_version, "source_status": r.source_status, "extraction_method": r.extraction_method,
                     "confidence": r.confidence, "verification_status": r.verification_status, "is_stale": r.is_stale, "content": r.content,
                     "notes": (r.extra or {}).get("notes", []), "last_verified_at": r.last_verified_at,
                     "evidence": [{"id": e.id, "url": e.url, "excerpt": e.excerpt, "source_section": e.source_section, "source_version": e.source_version,
                                   "raw_document_id": e.raw_document_id, "captured_at": e.captured_at} for e in ev]}}
