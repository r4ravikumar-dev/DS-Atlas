"""Server-side enforcement of invitation-only access: no direct account creation, every data endpoint requires
authentication (even with a known URL or record ID), session revocation via session_version, one-shot admin bootstrap."""
from __future__ import annotations

import re
import sys
import uuid

import jwt
import pytest

from app.core.security import create_session_token, hash_password
from app.database.session import SessionLocal
from app.models import User

PUBLIC = {"/api/v1/health", "/api/v1/ready", "/api/v1/meta", "/api/v1/auth/login", "/api/v1/auth/logout", "/api/v1/auth/me",
          "/api/v1/auth/invitations/validate", "/api/v1/auth/invitations/send-code", "/api/v1/auth/invitations/accept",
          # schema/docs: served only outside production (see create_app); they describe endpoints, not data
          "/api/v1/openapi.json", "/api/v1/docs", "/api/v1/docs/oauth2-redirect", "/api/v1/redoc"}


def _fresh_user(role: str = "viewer") -> tuple[str, str]:
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


def test_viewer_cannot_reach_admin_or_mutating_endpoints(client, as_viewer):
    for method, path in _routes():
        if method == "GET" and not path.startswith("/api/v1/admin"):
            continue
        r = client.request(method, _fill(path), json={}, headers=as_viewer)
        assert r.status_code in (403, 422), f"viewer got {r.status_code} on {method} {path}"


def test_direct_account_creation_is_removed(client, as_admin):
    r = client.post("/api/v1/admin/users", headers=as_admin, json={"email": "x@fixture.example", "password": "p" * 16, "role": "admin"})
    assert r.status_code == 405


def test_tokens_without_matching_session_version_are_rejected(client):
    uid, token = _fresh_user()
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 200
    claims = jwt.decode(token, options={"verify_signature": False})
    from app.core.config import get_settings
    for sv in (None, 0, 99):
        forged = {**claims, "sv": sv} if sv is not None else {k: v for k, v in claims.items() if k != "sv"}
        t = jwt.encode(forged, get_settings().secret_key, algorithm="HS256")
        assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {t}"}).status_code == 401


def test_admin_can_revoke_all_sessions(client, as_admin):
    uid, token = _fresh_user("researcher")
    h = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/v1/design-systems", headers=h).status_code == 200
    assert client.post(f"/api/v1/admin/users/{uid}/revoke-sessions", headers=as_admin).status_code == 200
    assert client.get("/api/v1/design-systems", headers=h).status_code == 401
    assert client.get("/api/v1/auth/me", headers=h).status_code == 401


@pytest.mark.parametrize("change", [{"role": "viewer"}, {"is_active": False}])
def test_role_change_or_deactivation_invalidates_sessions(client, as_admin, change):
    uid, token = _fresh_user("researcher")
    h = {"Authorization": f"Bearer {token}"}
    assert client.patch(f"/api/v1/admin/users/{uid}", headers=as_admin, json=change).status_code == 200
    assert client.get("/api/v1/auth/me", headers=h).status_code == 401


def test_non_privilege_update_keeps_sessions(client, as_admin):
    uid, token = _fresh_user()
    assert client.patch(f"/api/v1/admin/users/{uid}", headers=as_admin, json={"name": "FIXTURE renamed"}).status_code == 200
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 200


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


def test_public_invitation_endpoints_are_rate_limited(client):
    codes = [client.post("/api/v1/auth/invitations/send-code", json={"token": "x" * 43}).status_code for _ in range(12)]
    assert codes[:10] == [400] * 10 and codes[-1] == 429


def test_unauthenticated_responses_carry_noindex(client):
    r = client.get("/api/v1/design-systems")
    assert "noindex" in r.headers.get("x-robots-tag", "")
