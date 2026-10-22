"""SSRF guards, URL canonicalisation, safe redirects and source registration rules."""
import pytest

from app.scrapers.dskb import core


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "10.1.2.3", "192.168.0.10", "169.254.169.254", "[::1]", "0.0.0.0"])
def test_private_destinations_blocked(host):
    assert core.is_public_host(host) is False


def test_canonical_url_strips_tracking_and_fragments():
    assert core.canonical_url("HTTPS://Example.com/a/?utm_source=x&b=1#frag") == "https://example.com/a?b=1"
    assert core.canonical_url("https://example.com/") == "https://example.com/"


def test_redirect_to_private_ip_is_refused(monkeypatch):
    f = core.Fetcher()
    f.extra_allow = {"public.example"}
    f.ssrf_checked = {"public.example": True}

    class R:
        status_code = 302
        is_redirect = True
        headers = {"Location": "http://169.254.169.254/latest/meta-data"}

        def close(self):
            pass

    monkeypatch.setattr(f.session, "get", lambda *a, **k: R())
    with pytest.raises(core.UnsafeDestination):
        f._get_following_safe_redirects("https://public.example/x", {})


def test_fetcher_refuses_non_allowlisted_and_bad_scheme():
    f = core.Fetcher()
    assert f.get("https://not-approved.invalid/", source_id="T") is None
    assert f.get("file:///etc/passwd", source_id="T") is None


def test_source_registration_rules(client, as_admin, as_viewer):
    url = "/api/v1/sources"
    assert client.post(url, headers=as_viewer, json={"name": "x", "url": "https://ant.design/x"}).status_code == 403
    r = client.post(url, headers=as_admin, json={"name": "Plain http", "url": "http://ant.design/x"})
    assert r.status_code == 422
    r = client.post(url, headers=as_admin, json={"name": "Unapproved", "url": "https://unapproved-domain.example/docs"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "DOMAIN_NOT_APPROVED"
    r = client.post(url, headers=as_admin, json={"name": "Creds", "url": "https://user:pw@ant.design/x"})
    assert r.status_code == 422


def test_raw_snapshot_served_inert(client, as_admin, db):
    from app.models import RawDocument
    from app.services.storage import storage
    key = storage().put("raw/te/test-inert", b"<script>alert(1)</script>")
    d = RawDocument(content_sha256="f" * 64, storage_key=key, content_type="text/html", size_bytes=25, first_url="https://fixture.example")
    db.add(d)
    db.commit()
    r = client.get(f"/api/v1/documents/{d.id}/content", headers=as_admin)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/plain")
    assert "sandbox" in r.headers["content-security-policy"] and "attachment" in r.headers["content-disposition"]
