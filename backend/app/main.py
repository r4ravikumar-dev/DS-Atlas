"""FastAPI application factory: `uvicorn app.main:app`."""
from __future__ import annotations

import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .api.v1.routes import (administration, auth, comparisons, components, crawl_jobs, dashboard, documents, exports, guidelines, health,
                            quality, reports, search, sources, storybook, systems, tokens, verification)
from .core.config import get_settings
from .core.exceptions import install_handlers
from .core.logging import configure_logging, request_id_var

log = logging.getLogger("app.http")

TAGS = [
    {"name": "health", "description": "Liveness, readiness, metadata"},
    {"name": "auth", "description": "Session sign-in (httpOnly cookie + CSRF) or Bearer tokens"},
    {"name": "dashboard", "description": "Server-side aggregates"},
    {"name": "data-quality", "description": "Data-quality issues and the add-a-source workflow"},
    {"name": "sources", "description": "Source registry, coverage, URL queue, crawl initiation"},
    {"name": "crawl-jobs", "description": "Durable background jobs (crawl/build)"},
    {"name": "design-systems", "description": "Canonical, entity-resolved design systems"},
    {"name": "components", "description": "Component records and structured APIs"},
    {"name": "tokens", "description": "Design tokens, aliases and dependents"},
    {"name": "guidelines", "description": "Guidelines, specifications and patterns"},
    {"name": "search", "description": "Global full-text search"},
    {"name": "comparisons", "description": "Saved, evidence-labelled comparisons"},
    {"name": "reports", "description": "Generated research reports"},
    {"name": "exports", "description": "Asynchronous exports with protected downloads"},
    {"name": "documents", "description": "Raw snapshots and generic record access"},
    {"name": "administration", "description": "Users, audit trail, configuration, review queue"},
    {"name": "storybook", "description": "Storybook showcase projects, stories and component variants"},
    {"name": "verification", "description": "Official-documentation verification and field-level evidence"},
]


def create_app() -> FastAPI:
    s = get_settings()
    configure_logging()
    public_docs = s.environment != "production"  # the schema is published as backend/openapi.json; no live endpoint map in production
    app = FastAPI(title=s.app_name, version="1.0.0", openapi_url=f"{s.api_prefix}/openapi.json" if public_docs else None,
                  docs_url=f"{s.api_prefix}/docs" if public_docs else None, redoc_url=f"{s.api_prefix}/redoc" if public_docs else None, openapi_tags=TAGS,
                  description="Versioned REST API of the Design Systems Research Platform. Collection responses use `{data, meta}`; errors use `{error}`.")
    install_handlers(app)
    from .services import github_integration
    github_integration.configure()  # optional token; missing token = explicit unauthenticated mode (never fatal)
    if s.cors_origins:
        app.add_middleware(CORSMiddleware, allow_origins=s.cors_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        rid = request.headers.get("x-request-id") or f"req_{uuid.uuid4().hex[:16]}"
        if len(rid) > 64 or not rid.replace("_", "").replace("-", "").isalnum():
            rid = f"req_{uuid.uuid4().hex[:16]}"
        token = request_id_var.set(rid)
        t0 = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            request_id_var.reset(token)
            raise
        dur = int((time.perf_counter() - t0) * 1000)
        response.headers["X-Request-ID"] = rid
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("X-Robots-Tag", "noindex, nofollow, noarchive")  # private research platform: never indexed
        if not request.url.path.endswith(("/docs", "/redoc")):
            response.headers.setdefault("Cache-Control", "no-store")
        log.info("request", extra={"method": request.method, "path": request.url.path, "status": response.status_code, "duration_ms": dur})
        if dur > 1500:
            log.warning("slow request", extra={"path": request.url.path, "duration_ms": dur})
        request_id_var.reset(token)
        return response

    for r in (health, auth, dashboard, sources, crawl_jobs, systems, components, tokens, guidelines, search, comparisons, reports, exports,
              documents, administration, verification, storybook, quality):
        app.include_router(r.router, prefix=s.api_prefix)
    app.include_router(systems.resource_router, prefix=s.api_prefix)
    return app


app = create_app()
