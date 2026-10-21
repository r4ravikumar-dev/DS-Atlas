"""GitHub integration: token wiring from secret settings, usage telemetry and safe diagnostics.
Nothing here ever returns, logs or persists the token or an Authorization header."""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

import requests
from sqlalchemy import func, select

from ..core.config import get_settings
from ..database.session import SessionLocal
from ..models import ApiUsage
from ..scrapers.dskb import core as engine

log = logging.getLogger("app.github")


def configure() -> bool:
    """Apply the optional token from settings (env / .env / deployment secret) to the engine client and attach telemetry."""
    tok = get_settings().github_token
    if tok and tok.get_secret_value().strip():
        engine.GITHUB.token = tok.get_secret_value().strip()
    engine.GITHUB.on_usage = _persist_usage
    return engine.GITHUB.authenticated


def _persist_usage(d: dict[str, Any]) -> None:
    try:
        with SessionLocal() as db:
            db.add(ApiUsage(provider="github", endpoint=d["endpoint"][:500], status=d.get("status"), outcome=d["outcome"], authenticated=d["authenticated"],
                            rate_limit=d.get("rate_limit"), rate_remaining=d.get("rate_remaining"),
                            rate_reset_at=datetime.fromtimestamp(d["rate_reset"], timezone.utc) if d.get("rate_reset") else None,
                            rate_resource=d.get("rate_resource"), retry_after_s=d.get("retry_after_s")))
            db.commit()
    except Exception:  # telemetry must never break extraction
        log.warning("api usage telemetry failed", exc_info=True)


def diagnostics() -> dict[str, Any]:
    """Minimal live check: GET /rate_limit (does not consume the core quota)."""
    configure()
    present = engine.GITHUB.authenticated
    out: dict[str, Any] = {"checked_at": datetime.now(timezone.utc).isoformat(), "token_configured": present, "token_source": None, "mode": "authenticated" if present else "unauthenticated",
                           "api_version_header": engine.GITHUB.API_VERSION}
    if present:
        out["token_source"] = "GITHUB_TOKEN via backend settings (env/.env/secret store)"
    try:
        r = requests.get("https://api.github.com/rate_limit", headers=engine.GITHUB._headers(), timeout=15)
        out["http_status"] = r.status_code
        if r.status_code == 401:
            out["authentication"] = "invalid_credentials"
        elif r.ok:
            out["authentication"] = "valid" if present else "not_applicable"
            res = r.json().get("resources", {})
            out["rate_limits"] = {k: {"limit": v.get("limit"), "remaining": v.get("remaining"), "used": v.get("used"),
                                      "reset_at": datetime.fromtimestamp(v["reset"], timezone.utc).isoformat() if v.get("reset") else None}
                                  for k, v in res.items() if k in ("core", "search", "graphql", "code_search")}
        else:
            out["authentication"] = f"http_{r.status_code}"
    except requests.RequestException as e:
        out["authentication"] = "network_error"
        out["error"] = type(e).__name__
    with SessionLocal() as db:
        rows = db.execute(select(ApiUsage.outcome, ApiUsage.authenticated, func.count()).where(ApiUsage.provider == "github")
                          .group_by(ApiUsage.outcome, ApiUsage.authenticated)).all()
        out["usage_since_telemetry_enabled"] = [{"outcome": o, "authenticated": a, "requests": n} for o, a, n in rows]
        last = db.scalar(select(ApiUsage).where(ApiUsage.provider == "github", ApiUsage.rate_remaining.is_not(None)).order_by(ApiUsage.id.desc()).limit(1))
        out["last_observed_rate_state"] = {"limit": last.rate_limit, "remaining": last.rate_remaining, "reset_at": last.rate_reset_at.isoformat() if last.rate_reset_at else None,
                                           "observed_at": last.ts.isoformat()} if last else None
    out["engine_requests_this_process"] = engine.GITHUB.calls
    return out
