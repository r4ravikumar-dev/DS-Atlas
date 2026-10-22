from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text

from ....core.config import get_settings
from ....database.session import SessionLocal
from ....scrapers.dskb.core import SCHEMA_VERSION
from ....scrapers.dskb.sources import TAXONOMY
from ...deps import require

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness")
def health():
    return {"status": "ok"}


@router.get("/ready", summary="Readiness (database + migrations)")
def ready():
    checks = {}
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
            checks["database"] = "ok"
            checks["migration"] = db.execute(text("SELECT version_num FROM alembic_version")).scalar() or "missing"
            checks["worker_heartbeat"] = "ok" if db.execute(text(
                "SELECT count(*) FROM jobs WHERE status='running' AND heartbeat_at < now() - interval '10 minutes'")).scalar() == 0 else "stale_jobs"
    except Exception:
        checks["database"] = "unavailable"
        return JSONResponse({"status": "not_ready", "checks": checks}, status_code=503)
    return {"status": "ready", "checks": checks}


@router.get("/meta", summary="API metadata & taxonomy", dependencies=[Depends(require("public:read"))])
def meta():
    s = get_settings()
    return {"data": {"name": s.app_name, "api_version": "v1", "record_schema_version": SCHEMA_VERSION, "environment": s.environment,
                     "max_page_size": s.max_page_size,
                     "taxonomy": [{"id": k, "name": v["name"], "subcategories": v["subs"]} for k, v in TAXONOMY.items()],
                     "verification_statuses": ["verified", "partially_verified", "unverified"],
                     "job_statuses": ["queued", "running", "succeeded", "partially_succeeded", "failed", "cancelled"]}}
