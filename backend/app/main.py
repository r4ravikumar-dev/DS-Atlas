"""FastAPI application factory: `uvicorn app.main:app`."""
from __future__ import annotations

import json
import logging
import hmac
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from .api import public_projection

from .api.v1.routes import (administration, auth, comparisons, components, crawl_jobs, dashboard, documents, exports, guidelines, health,
                            public, quality, reports, search, sources, storybook, sync, systems, tokens, verification)
from .core.config import get_settings
from .core.exceptions import install_handlers
from .core.logging import configure_logging, request_id_var

log = logging.getLogger("app.http")

TAGS = [
    {"name": "health", "description": "Liveness, readiness, metadata"},
    {"name": "auth", "description": "Session sign-in (httpOnly cookie + CSRF) or Bearer tokens"},
    {"name": "dashboard", "description": "Server-side aggregates"},
    {"name": "data-quality", "description": "Data-quality issues and the add-a-source workflow"},
    {"name": "public", "description": "Public read-only extras: stats and comparisons"},
    {"name": "sync", "description": "Daily synchronization (administrator) and the cron entry point"},
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

    public_prefixes = tuple(f"{s.api_prefix}{x}" for x in ("/design-systems", "/components", "/tokens", "/guidelines", "/patterns", "/search",
                                                            "/storybook/projects", "/storybook/stories", "/storybook/variants", "/compare",
                                                            "/stats", "/meta", "/resources"))
    hits: dict[str, list[float]] = {}

    def _limited(request: Request) -> bool:
        """Anonymous clients: sliding window per IP (per instance; put a CDN/firewall rule in front for global limits)."""
        if request.headers.get("authorization") or request.cookies.get("dsrp_session") or not request.url.path.startswith(s.api_prefix):
            return False
        # the site's own server-side rendering shares a few egress IPs; it identifies itself with RENDER_API_KEY
        key = s.render_api_key.get_secret_value() if s.render_api_key else ""
        if key and hmac.compare_digest(request.headers.get("x-render-key", "").encode(), key.encode()):
            return False
        ip = (request.headers.get("x-forwarded-for") or (request.client.host if request.client else "?")).split(",")[0].strip()
        t = time.time()
        w = [x for x in hits.get(ip, []) if t - x < 60]
        w.append(t)
        hits[ip] = w
        if len(hits) > 50_000:
            hits.clear()
        return len(w) > s.public_rate_limit_per_minute

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        rid = request.headers.get("x-request-id") or f"req_{uuid.uuid4().hex[:16]}"
        if len(rid) > 64 or not rid.replace("_", "").replace("-", "").isalnum():
            rid = f"req_{uuid.uuid4().hex[:16]}"
        token = request_id_var.set(rid)
        if _limited(request):
            request_id_var.reset(token)
            return JSONResponse({"error": {"code": "RATE_LIMITED", "message": "Too many requests. Please slow down.", "details": [], "request_id": rid}},
                                status_code=429, headers={"Retry-After": "60", "X-Request-ID": rid})
        t0 = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            request_id_var.reset(token)
            raise
        dur = int((time.perf_counter() - t0) * 1000)
        public_view = getattr(request.state, "public_view", None)
        if public_view and response.status_code == 200 and response.headers.get("content-type", "").startswith("application/json"):
            body = b"".join([chunk async for chunk in response.body_iterator])
            try:
                data = public_projection.project(request.url.path, json.loads(body))
                headers = {k: v for k, v in response.headers.items() if k.lower() not in ("content-length", "content-type")}
                response = JSONResponse(data, status_code=200, headers=headers)
            except ValueError:
                response = Response(body, status_code=200, headers=dict(response.headers))
        if public_view is False:
            # an administrator's full view of a public URL must never be stored by a shared cache
            response.headers["Cache-Control"] = "private, no-store"
        response.headers["X-Request-ID"] = rid
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("X-Robots-Tag", "noindex, nofollow, noarchive")  # private research platform: never indexed
        if (request.method == "GET" and response.status_code == 200 and request.url.path.startswith(public_prefixes)
                and "set-cookie" not in response.headers):
            # published data: shared caches may keep it briefly; the daily sync changes it at most once a day
            response.headers.setdefault("Cache-Control", "public, max-age=60, s-maxage=300, stale-while-revalidate=600")
            response.headers.setdefault("Vary", "Accept-Encoding, Cookie, Authorization")
        elif not request.url.path.endswith(("/docs", "/redoc")):
            response.headers.setdefault("Cache-Control", "no-store")
        log.info("request", extra={"method": request.method, "path": request.url.path, "status": response.status_code, "duration_ms": dur})
        if dur > 1500:
            log.warning("slow request", extra={"path": request.url.path, "duration_ms": dur})
        request_id_var.reset(token)
        return response

    for r in (health, auth, dashboard, sources, crawl_jobs, systems, components, tokens, guidelines, search, comparisons, reports, exports,
              documents, administration, verification, storybook, quality, public, sync):
        app.include_router(r.router, prefix=s.api_prefix)
    app.include_router(systems.resource_router, prefix=s.api_prefix)
    return app


app = create_app()
