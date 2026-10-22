"""Server-side enforcement of the private single-administrator model: every data endpoint requires an administrator session
(even with a known URL or record ID), no registration, session revocation via session_version, one-shot admin bootstrap."""
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


def _routes():
    # Enumerate from the generated OpenAPI document (FastAPI wraps included routers, so app.routes is not flat).
    from app.main import app
    for path, ops in app.openapi()["paths"].items():
        if path not in PUBLIC:
            for m in ops:
                yield m.upper(), path


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


def test_non_admin_sessions_are_refused_everywhere(client, as_viewer):
    for method, path in _routes():
        r = client.request(method, _fill(path), json={}, headers=as_viewer)
        assert r.status_code in (403, 422), f"non-admin got {r.status_code} on {method} {path}"


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
