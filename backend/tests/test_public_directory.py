"""Additions for the public directory experience: availability filters, headline stats, public search links,
the not-inspected comparison state, and targeted frontend cache refresh after builds."""
import httpx
from pydantic import SecretStr

from app.core.config import get_settings
from app.services import frontend_cache


def test_system_availability_filters(client, built_kb):
    every = client.get("/api/v1/design-systems", params={"page_size": 100}).json()["data"]
    with_tokens = client.get("/api/v1/design-systems", params={"has_tokens": "true", "page_size": 100}).json()["data"]
    with_comps = client.get("/api/v1/design-systems", params={"has_components": "true", "page_size": 100}).json()["data"]
    assert {s["id"] for s in with_tokens} == {s["id"] for s in every if s["token_count"] > 0}
    assert {s["id"] for s in with_comps} == {s["id"] for s in every if s["component_count"] > 0}
    assert with_comps, "the fixture build has at least one system with components"


def test_stats_report_contributing_sources(client, built_kb):
    data = client.get("/api/v1/stats").json()["data"]
    assert isinstance(data["sources_indexed"], int) and data["sources_indexed"] >= 1


def test_search_links_point_at_public_pages(client, built_kb):
    hits = client.get("/api/v1/search", params={"q": "fixture", "page_size": 50}).json()["data"]
    assert hits
    for h in hits:
        assert not h["url"].startswith("/platform")
        if h["type"] in ("system", "component", "token", "guideline", "pattern"):
            assert not h["url"].startswith("/admin"), h


def test_comparison_states_are_known(client, built_kb):
    ids = [c["id"] for c in client.get("/api/v1/components", params={"page_size": 2}).json()["data"]]
    r = client.get("/api/v1/compare", params={"kind": "components", "ids": ",".join(map(str, ids))})
    assert r.status_code == 200, r.text
    res = r.json()["data"]["result"] if "result" in r.json()["data"] else r.json()["data"]
    states = {c["status"] for row in res["rows"].values() for cells in row.values() for c in cells}
    assert states <= {"documented", "not_documented", "not_inspected", "not_applicable"}


def test_cache_tags_only_when_content_changed():
    unchanged = {"changes": {"systems": {"created": 0, "updated": 0, "removed": 0, "unchanged": 4}, "relationships": {"added": 0, "removed": 0}}}
    assert frontend_cache.tags_for(unchanged) == []
    changed = {"changes": {"systems": {"updated": 1}, "tokens": {"created": 2}, "relationships": {"added": 0, "removed": 0}},
               "changed_ids": {"systems": [7], "tokens": [11, 12], "components": []}}
    tags = frontend_cache.tags_for(changed)
    assert {"stats", "search", "systems", "tokens", "system:7", "token:11", "token:12"} <= set(tags)
    assert "components" not in tags


def test_notify_posts_tags_with_bearer_and_skips_when_unconfigured(monkeypatch):
    calls = []
    monkeypatch.setattr(httpx, "post", lambda url, json, headers, timeout: calls.append((url, json, headers)) or httpx.Response(200, request=httpx.Request("POST", url)))
    summary = {"changes": {"systems": {"updated": 1}}, "changed_ids": {"systems": [3]}}
    monkeypatch.setattr(get_settings(), "frontend_revalidate_url", None)
    assert frontend_cache.notify(summary) is False and calls == []
    monkeypatch.setattr(get_settings(), "frontend_revalidate_url", "https://site.example/revalidate")
    monkeypatch.setattr(get_settings(), "revalidate_secret", SecretStr("s3cret-fixture"))
    assert frontend_cache.notify(summary) is True
    url, body, headers = calls[0]
    assert url == "https://site.example/revalidate" and "system:3" in body["tags"] and headers["Authorization"] == "Bearer s3cret-fixture"
    assert frontend_cache.notify({"changes": {}}) is False and len(calls) == 1


def test_render_key_exempts_site_rendering_from_anonymous_rate_limit(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "render_api_key", SecretStr("render-fixture-key"))
    monkeypatch.setattr(get_settings(), "public_rate_limit_per_minute", 3)
    ip = {"X-Forwarded-For": "203.0.113.99"}
    assert [client.get("/api/v1/meta", headers={**ip, "x-render-key": "render-fixture-key"}).status_code for _ in range(6)] == [200] * 6
    codes = [client.get("/api/v1/meta", headers={**ip, "x-render-key": "wrong"}).status_code for _ in range(6)]
    assert 429 in codes
