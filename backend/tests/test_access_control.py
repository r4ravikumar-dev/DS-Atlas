"""Public directory + private administration, enforced server-side: published data is readable without an account; every
other endpoint requires an administrator session (even with a known URL or record ID); no registration; session revocation
via session_version; one-shot admin bootstrap; the cron entry point needs its secret."""
from __future__ import annotations

import re
import sys
import uuid

import jwt
import pytest

from app.core.security import create_session_token, hash_password
from app.database.session import SessionLocal
from app.models import User

PUBLIC = {"/api/v1/health", "/api/v1/ready", "/api/v1/auth/login", "/api/v1/auth/logout", "/api/v1/auth/me", "/api/v1/auth/password",
          # schema/docs: served only outside production (see create_app); they describe endpoints, not data
          "/api/v1/openapi.json", "/api/v1/docs", "/api/v1/docs/oauth2-redirect", "/api/v1/redoc"}


def _fresh_user(role: str = "admin") -> tuple[str, str]:
    with SessionLocal() as s:
        u = User(email=f"fx-{uuid.uuid4().hex[:8]}@fixture.example", name="FIXTURE", password_hash=hash_password("fixture-password-123"), role=role)
        s.add(u)
        s.commit()
        return str(u.id), create_session_token(str(u.id), role, u.session_version)


PUBLIC_READ_PREFIXES = ("/api/v1/design-systems", "/api/v1/components", "/api/v1/tokens", "/api/v1/guidelines", "/api/v1/patterns",
                        "/api/v1/search", "/api/v1/storybook/projects", "/api/v1/storybook/stories", "/api/v1/storybook/variants",
                        "/api/v1/compare", "/api/v1/stats", "/api/v1/meta", "/api/v1/resources", "/api/v1/pattern-library")


def _all_routes():
    # Enumerate from the generated OpenAPI document (FastAPI wraps included routers, so app.routes is not flat).
    from app.main import app
    for path, ops in app.openapi()["paths"].items():
        if path not in PUBLIC:
            for m in ops:
                yield m.upper(), path


def _is_public_read(method: str, path: str) -> bool:
    # asset provenance and retrieval diagnostics are administrator-only, even though they hang off a system URL
    return method == "GET" and path.startswith(PUBLIC_READ_PREFIXES) and not path.startswith("/api/v1/resources/verify") and not path.endswith("/assets")


def _routes():
    """Private endpoints only."""
    return [(m, p) for m, p in _all_routes() if not _is_public_read(m, p)]


def _public_routes():
    return [(m, p) for m, p in _all_routes() if _is_public_read(m, p)]


def _fill(path: str) -> str:
    # Any well-formed ID: authorization must be decided before the record is looked up.
    return re.sub(r"\{[^}]+\}", lambda m: "1" if m.group(0) in ("{item_id}", "{group_id}") else str(uuid.uuid4()), path)


def test_every_non_public_endpoint_rejects_anonymous_requests(client):
    client.cookies.clear()
    checked = 0
    for method, path in _routes():
        r = client.request(method, _fill(path), json={})
        assert r.status_code == 401, f"{method} {path} returned {r.status_code} without credentials"
        checked += 1
    assert checked > 40


def test_non_admin_sessions_are_refused_on_every_private_endpoint(client, as_viewer):
    for method, path in _routes():
        r = client.request(method, _fill(path), json={}, headers=as_viewer)
        assert r.status_code in (403, 422), f"non-admin got {r.status_code} on {method} {path}"


def test_published_data_is_readable_without_an_account(client):
    client.cookies.clear()
    routes = _public_routes()
    assert len(routes) > 20
    for method, path in routes:
        r = client.request(method, _fill(path))
        assert r.status_code not in (401, 403), f"public {method} {path} returned {r.status_code}"


def test_public_writes_are_refused(client):
    client.cookies.clear()
    for method, path in [("PATCH", "/api/v1/design-systems/1"), ("POST", "/api/v1/design-systems/1/resources"), ("POST", "/api/v1/intake"),
                         ("POST", "/api/v1/admin/sync/run"), ("POST", "/api/v1/sources"), ("POST", "/api/v1/crawl-jobs"), ("POST", "/api/v1/comparisons")]:
        assert client.request(method, path, json={}).status_code == 401, f"{method} {path}"


def test_public_pages_are_cacheable_private_ones_are_not(client, as_admin):
    client.cookies.clear()
    pub = client.get("/api/v1/design-systems")
    assert pub.status_code == 200 and "public" in pub.headers["cache-control"]
    assert client.get("/api/v1/admin/sync", headers=as_admin).headers["cache-control"] == "no-store"


def test_cron_entry_point_requires_its_secret(client, monkeypatch):
    from pydantic import SecretStr
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), "cron_secret", None)
    assert client.get("/api/v1/internal/cron/sync").status_code == 404  # disabled unless configured
    monkeypatch.setattr(get_settings(), "cron_secret", SecretStr("fixture-cron-secret-value"))
    assert client.get("/api/v1/internal/cron/sync").status_code == 401
    assert client.get("/api/v1/internal/cron/sync", headers={"Authorization": "Bearer wrong"}).status_code == 401
    ok = client.get("/api/v1/internal/cron/sync", headers={"Authorization": "Bearer fixture-cron-secret-value"})
    assert ok.status_code == 200 and "next_run_at" in ok.json()["data"]


def test_anonymous_api_traffic_is_rate_limited(client, monkeypatch):
    from app.core.config import get_settings
    client.cookies.clear()
    monkeypatch.setattr(get_settings(), "public_rate_limit_per_minute", 5)
    codes = [client.get("/api/v1/stats", headers={"X-Forwarded-For": "203.0.113.77"}).status_code for _ in range(7)]
    assert codes[:5] == [200] * 5 and codes[-1] == 429


def test_tokens_without_matching_session_version_are_rejected(client):
    uid, token = _fresh_user()
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 200
    claims = jwt.decode(token, options={"verify_signature": False})
    from app.core.config import get_settings
    for sv in (None, 0, 99):
        forged = {**claims, "sv": sv} if sv is not None else {k: v for k, v in claims.items() if k != "sv"}
        t = jwt.encode(forged, get_settings().secret_key, algorithm="HS256")
        assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {t}"}).status_code == 401


def test_password_change_revokes_other_sessions(client):
    uid, token = _fresh_user()
    other = {"Authorization": f"Bearer {token}"}
    r = client.post("/api/v1/auth/password", headers=other, json={"current_password": "wrong", "new_password": "a-new-long-password"})
    assert r.status_code == 400
    r = client.post("/api/v1/auth/password", headers=other, json={"current_password": "fixture-password-123", "new_password": "a-new-long-password"})
    assert r.status_code == 200
    assert client.get("/api/v1/auth/me", headers=other).status_code == 401  # the old token is now stale
    with SessionLocal() as s:
        email = s.get(User, uuid.UUID(uid)).email
    assert client.post("/api/v1/auth/login", json={"email": email, "password": "a-new-long-password"}).status_code == 200
    client.cookies.clear()


def test_short_new_password_rejected(client):
    _, token = _fresh_user()
    r = client.post("/api/v1/auth/password", headers={"Authorization": f"Bearer {token}"},
                    json={"current_password": "fixture-password-123", "new_password": "short"})
    assert r.status_code == 422


def test_login_session_survives_until_revoked(client):
    uid, _ = _fresh_user()
    with SessionLocal() as s:
        email = s.get(User, uuid.UUID(uid)).email
    r = client.post("/api/v1/auth/login", json={"email": email, "password": "fixture-password-123"})
    assert r.status_code == 200
    with SessionLocal() as s:
        s.get(User, uuid.UUID(uid)).session_version += 1
        s.commit()
    assert client.get("/api/v1/auth/me").status_code == 401  # cookie from login is now stale
    client.cookies.clear()


def test_bootstrap_admin_refuses_when_an_admin_exists(monkeypatch, users):
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "scripts"))
    import manage
    monkeypatch.setenv("ADMIN_EMAIL", "second-admin@fixture.example")
    monkeypatch.setenv("ADMIN_PASSWORD", "a-long-enough-password")
    monkeypatch.setattr(sys, "argv", ["manage.py", "bootstrap-admin"])
    with pytest.raises(SystemExit) as e:
        manage.main()
    assert "already exists" in str(e.value)
    with SessionLocal() as s:
        assert not s.query(User).filter(User.email == "second-admin@fixture.example").first()


def test_login_is_rate_limited_per_client(client):
    codes = [client.post("/api/v1/auth/login", json={"email": f"n{i}@fixture.example", "password": "x"}).status_code for i in range(31)]
    assert codes[:30] == [401] * 30 and codes[-1] == 429


def test_reset_admin_password_cli_requires_existing_admin(monkeypatch):
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "scripts"))
    import manage
    monkeypatch.setenv("ADMIN_PASSWORD", "another-long-password")
    monkeypatch.setattr(sys, "argv", ["manage.py", "reset-admin-password", "nobody@fixture.example"])
    with pytest.raises(SystemExit) as e:
        manage.main()
    assert "No administrator" in str(e.value)


def test_unauthenticated_responses_carry_noindex(client):
    r = client.get("/api/v1/design-systems")
    assert "noindex" in r.headers.get("x-robots-tag", "")
