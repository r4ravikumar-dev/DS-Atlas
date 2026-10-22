"""Health, auth, CSRF, RBAC, validation and error-envelope behaviour."""
from conftest import FIXTURE_PW


def test_health_ready_meta(client):
    assert client.get("/api/v1/health").json() == {"status": "ok"}
    r = client.get("/api/v1/ready").json()
    assert r["status"] == "ready" and r["checks"]["database"] == "ok"
    assert client.get("/api/v1/meta").status_code == 200  # taxonomy is public


def test_request_id_header_and_security_headers(client):
    r = client.get("/api/v1/health", headers={"X-Request-ID": "req_abc123"})
    assert r.headers["X-Request-ID"] == "req_abc123"
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    bad = client.get("/api/v1/health", headers={"X-Request-ID": "<script>"})
    assert bad.headers["X-Request-ID"].startswith("req_") and "<" not in bad.headers["X-Request-ID"]


def test_anonymous_is_rejected_with_error_envelope(client):
    r = client.get("/api/v1/sources")
    assert r.status_code == 401
    err = r.json()["error"]
    assert err["code"] == "UNAUTHENTICATED" and err["request_id"]


def test_login_sets_httponly_session_and_csrf(client, users):
    r = client.post("/api/v1/auth/login", json={"email": users["admin"]["email"], "password": FIXTURE_PW})
    assert r.status_code == 200
    cookies = r.headers.get_list("set-cookie")
    session = next(c for c in cookies if c.startswith("dsrp_session="))
    csrf = next(c for c in cookies if c.startswith("dsrp_csrf="))
    assert "HttpOnly" in session and "SameSite=lax" in session
    assert "HttpOnly" not in csrf
    assert r.json()["data"]["user"]["role"] == "admin"
    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200 and me.json()["data"]["email"] == users["admin"]["email"]
    client.cookies.clear()


def test_wrong_password_and_rate_limit(client, users):
    for _ in range(10):
        assert client.post("/api/v1/auth/login", json={"email": "nobody@fixture.example", "password": "x"}).status_code == 401
    r = client.post("/api/v1/auth/login", json={"email": "nobody@fixture.example", "password": "x"})
    assert r.status_code == 429 and r.json()["error"]["code"] == "RATE_LIMITED"


def test_csrf_required_for_cookie_authenticated_mutations(client, users):
    client.post("/api/v1/auth/login", json={"email": users["admin"]["email"], "password": FIXTURE_PW})
    body = {"name": "x", "kind": "systems", "item_ids": [1, 2]}
    r = client.post("/api/v1/comparisons", json=body)
    assert r.status_code == 403 and r.json()["error"]["code"] == "CSRF_FAILED"
    r2 = client.post("/api/v1/comparisons", json=body, headers={"X-CSRF-Token": "wrong"})
    assert r2.status_code == 403
    token = client.cookies.get("dsrp_csrf")
    r3 = client.post("/api/v1/comparisons", json=body, headers={"X-CSRF-Token": token})
    assert r3.status_code != 403  # passes CSRF (may 422 on unknown ids)
    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": token})
    client.cookies.clear()


def test_only_administrators_are_authorized(client, as_viewer, as_researcher, as_admin, fixture_source):
    """Legacy non-admin accounts hold valid sessions but get only what the public gets."""
    for h in (as_viewer, as_researcher):
        assert client.get("/api/v1/design-systems", headers=h).status_code == 200  # public data
        assert client.get("/api/v1/dashboard/summary", headers=h).status_code == 403
        assert client.post(f"/api/v1/sources/{fixture_source}/crawl", headers=h).status_code == 403
        assert client.get("/api/v1/export-jobs", headers=h).status_code == 403
        assert client.patch("/api/v1/admin/configuration", headers=h, json={}).status_code == 403
    assert client.get("/api/v1/design-systems", headers=as_admin).status_code == 200


def test_non_admin_cannot_sign_in(client, users):
    r = client.post("/api/v1/auth/login", json={"email": users["viewer"]["email"], "password": FIXTURE_PW})
    assert r.status_code == 401
    client.cookies.clear()


def test_validation_errors(client, as_admin):
    r = client.get("/api/v1/sources?page_size=1000", headers=as_admin)
    assert r.status_code == 422
    e = r.json()["error"]
    assert e["code"] == "VALIDATION_ERROR" and e["details"][0]["field"] == "page_size"
    assert client.get("/api/v1/design-systems?verification=bogus", headers=as_admin).status_code == 422


def test_user_management_and_registration_endpoints_do_not_exist(client, as_admin):
    assert client.get("/api/v1/admin/users", headers=as_admin).status_code == 404
    assert client.post("/api/v1/admin/users", headers=as_admin, json={}).status_code in (404, 405)
    assert client.post("/api/v1/auth/register", json={}).status_code == 404
    assert client.post("/api/v1/auth/invitations/accept", json={}).status_code == 404


def test_config_validation_and_no_secrets(client, as_admin):
    cfg = client.get("/api/v1/admin/configuration", headers=as_admin).json()["data"]
    flat = str(cfg).lower()
    assert "secret" not in flat and "password" not in flat and "database_url" not in flat
    assert client.patch("/api/v1/admin/configuration", headers=as_admin, json={"approved_domains": ["not a domain"]}).status_code == 422
