"""System-scoped hierarchy (slugs, families, token groups, patterns), the public presentation model, playground schemas and
visual-asset discovery. All data is FIXTURE."""
from __future__ import annotations

from app.api.public_projection import INTERNAL_FIELDS, project
from app.database.session import SessionLocal
from app.models import Component, DesignSystem, DesignToken, SystemAsset
from app.services import assets, catalog, playground


def _fixture_system(client):
    return next(s for s in client.get("/api/v1/design-systems", params={"q": "fixture"}).json()["data"] if s["name"] == "Fixture UI")


def test_systems_resolve_by_stable_slug_and_scope_their_records(client, built_kb):
    s = _fixture_system(client)
    assert s["slug"] == "fixture-ui"
    by_slug = client.get("/api/v1/design-systems/fixture-ui").json()["data"]
    assert by_slug["id"] == s["id"]
    comps = client.get("/api/v1/design-systems/fixture-ui/components").json()["data"]
    assert comps and all(c["system_slug"] == "fixture-ui" and c["system_name"] == "Fixture UI" for c in comps)
    dialog = next(c for c in comps if c["name"] == "Dialog")
    assert dialog["slug"] == "dialog" and dialog["family_category"] == "Overlays and floating interfaces"
    one = client.get("/api/v1/design-systems/fixture-ui/components/dialog").json()["data"]
    assert one["id"] == dialog["id"] and [p["name"] for p in one["props"]] == ["open", "defaultOpen", "onOpenChange"]
    assert client.get("/api/v1/design-systems/fixture-ui/components/does-not-exist").status_code == 404


def test_a_component_is_not_served_under_another_system(client, built_kb):
    with SessionLocal() as db:
        other = DesignSystem(key="dsys:fixture-other", slug="fixture-other", name="FIXTURE Other", verification_status="unverified")
        db.add(other)
        db.commit()
        cid = db.query(Component).filter(Component.name == "Dialog").first().id
        try:
            assert client.get(f"/api/v1/design-systems/fixture-other/components/{cid}").status_code == 404
            assert client.get("/api/v1/design-systems/fixture-other/components").json()["meta"]["total_items"] == 0
        finally:
            db.delete(other)
            db.commit()


def test_families_and_token_groups_count_real_records(client, built_kb):
    fams = client.get("/api/v1/design-systems/fixture-ui/component-families").json()["data"]
    total = client.get("/api/v1/design-systems/fixture-ui/components").json()["meta"]["total_items"]
    assert sum(c["count"] for c in fams) == total
    assert {f["name"] for c in fams for f in c["families"]} >= {"Dialog"}
    with SessionLocal() as db:  # the FIXTURE build leaves tokens unlinked; link them to exercise the scoped views
        sid = db.query(DesignSystem).filter(DesignSystem.slug == "fixture-ui").one().id
        db.execute(DesignToken.__table__.update().values(system_id=sid))
        db.commit()
    groups = client.get("/api/v1/design-systems/fixture-ui/token-groups").json()["data"]
    n = client.get("/api/v1/design-systems/fixture-ui/tokens").json()["meta"]["total_items"]
    assert groups["categories"] == [{"value": "color", "count": n}]
    tiers = {t["value"] for t in groups["tiers"]}
    assert tiers == {"primitive", "semantic"}  # --fx-brand holds a value; --fx-primary aliases it
    toks = client.get("/api/v1/design-systems/fixture-ui/tokens", params={"tier": "semantic"}).json()["data"]
    assert {t["path"] for t in toks} == {"--fx-primary"} and toks[0]["system_slug"] == "fixture-ui"
    slug = toks[0]["slug"]
    detail = client.get(f"/api/v1/design-systems/fixture-ui/tokens/{slug}").json()["data"]
    assert detail["alias_of"] == "--fx-brand"


def test_catalog_refresh_is_idempotent_and_never_renames(built_kb):
    with SessionLocal() as db:
        before = db.query(Component.id, Component.slug).all()
        second = catalog.refresh(db)
        db.commit()
        assert second["system_slugs"] == second["component_slugs"] == second["token_slugs"] == second["token_categories"] == 0
        assert db.query(Component.id, Component.slug).all() == before


def test_public_view_omits_internal_status_but_admins_see_it(client, as_admin, built_kb):
    anon = client.get("/api/v1/design-systems/fixture-ui")
    data = anon.json()["data"]
    def keys(v):
        if isinstance(v, dict):
            return set(v) | {k for x in v.values() for k in keys(x)}
        if isinstance(v, list):
            return {k for x in v for k in keys(x)}
        return set()
    assert not keys(data) & INTERNAL_FIELDS
    assert data["name"] == "Fixture UI" and "resources" in data and anon.headers["cache-control"].startswith("public")
    comps = client.get("/api/v1/components").json()["data"]
    assert comps and all("verification_status" not in c and "source_key" not in c for c in comps)
    admin = client.get("/api/v1/design-systems/fixture-ui", headers=as_admin)
    assert "verification_status" in admin.json()["data"] and admin.headers["cache-control"] == "private, no-store"


def test_projection_keeps_content_and_drops_invalid_links():
    body = {"data": {"name": "X", "verification_status": "verified", "resources": [
        {"resource_type": "github_repository", "url": "https://github.com/x/y", "verification_status": "verified", "evidence_note": "n"},
        {"resource_type": "official_website", "url": "https://dead.example", "verification_status": "invalid"}],
        "rows": {"overview": {"A": [{"status": "documented", "value": 1}]}}}}
    out = project("/api/v1/design-systems/1", body)["data"]
    assert out["resources"] == [{"resource_type": "github_repository", "url": "https://github.com/x/y"}]
    assert out["rows"]["overview"]["A"][0]["status"] == "documented"  # content "status" is kept outside Storybook paths
    assert "status" not in project("/api/v1/storybook/projects", {"data": [{"title": "S", "status": "failed"}]})["data"][0]


def test_playground_schema_uses_documented_props_and_marks_provenance(client, built_kb, monkeypatch):
    reg = {"libraries": {"Fixture UI": {"key": "fixture", "package": "fixture-ui", "version": "1.0.0", "tier": "live", "themes": ["light"],
                                        "styling": "FIXTURE"}},
           "components": [{"library": "Fixture UI", "component": "Dialog", "impl": "Dialog", "props": ["defaultOpen", "onOpenChange", "missing"],
                           "extra": {"size": {"type": "enum", "options": ["sm", "md"], "default": "md"}}, "content": {"title": "Hello"}}]}
    monkeypatch.setattr(playground, "registry", lambda: reg)
    cid = client.get("/api/v1/design-systems/fixture-ui/components/dialog").json()["data"]["id"]
    sch = client.get(f"/api/v1/components/{cid}/playground-schema").json()["data"]
    assert sch["tier"] == "live" and sch["implementation"]["key"] == "fixture.Dialog"
    ctl = {c["name"]: c for c in sch["controls"]}
    assert set(ctl) == {"defaultOpen", "size", "title"}  # handlers and undocumented names are never controls
    assert ctl["defaultOpen"]["kind"] == "boolean" and ctl["defaultOpen"]["default"] is False and ctl["defaultOpen"]["default_source"] == "documented"
    assert ctl["size"]["provenance"] == "implementation" and ctl["size"]["default_source"] == "implementation"
    assert ctl["title"]["provenance"] == "preview" and ctl["title"]["default_source"] == "preview"
    assert "onOpenChange" in sch["metadata_only_props"]


def test_components_without_a_recipe_are_documentation_only(client, built_kb):
    cid = next(c["id"] for c in client.get("/api/v1/components").json()["data"] if c["name"] == "Legacy")
    sch = client.get(f"/api/v1/components/{cid}/playground-schema").json()["data"]
    assert sch["tier"] == "docs" and sch["controls"] == [] and sch["limitations"]


def test_type_parsing_offers_only_safe_controls():
    assert playground.parse_type("`large` | `medium` | `small`") == {"kind": "enum", "options": ["large", "medium", "small"]}
    assert playground.parse_type('horizontal" | "vertical" | undefined') == {"kind": "enum", "options": ["horizontal", "vertical"]}
    assert playground.parse_type("boolean | { delay: number }") == {"kind": "boolean"}
    for unsafe in ("(open: boolean) => void", "React.ReactNode", "MantineSize | number", "string | number"):
        assert playground.parse_type(unsafe) is None
    assert playground.parse_default('`primary` when `variant="solid"`', {"kind": "enum", "options": ["primary"]}) == (None, False)


def test_asset_discovery_reads_only_what_the_page_declares():
    page = ('<link rel="icon" href="/favicon.ico"><link rel="icon" type="image/svg+xml" href="/mark.svg">'
            '<link rel="apple-touch-icon" href="/touch.png"><meta property="og:image" content="/og.png"><link rel="icon" href="data:,">')
    found = assets.parse_page(page, "https://ds.example/docs/")
    assert found["icons"] == ["https://ds.example/mark.svg", "https://ds.example/touch.png", "https://ds.example/favicon.ico"]
    assert found["social"] == "https://ds.example/og.png"
    png = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + (180).to_bytes(4, "big") + (180).to_bytes(4, "big") + b"\x00" * 64
    assert assets.image_size(png, "image/png") == (180, 180) and assets.sniff(png) == "image/png"


def test_public_assets_skip_broken_and_tiny_icons(built_kb):
    with SessionLocal() as db:
        sid = db.query(DesignSystem).filter(DesignSystem.slug == "fixture-ui").one().id
        rows = [SystemAsset(system_id=sid, kind="icon", url="https://fixture.example/tiny.png", mime="image/png", width=16, height=16, status="ok", is_primary=True),
                SystemAsset(system_id=sid, kind="social_image", url="https://fixture.example/og.png", mime="image/png", width=1200, height=630,
                            status="broken", is_primary=True)]
        db.add_all(rows)
        db.commit()
        try:
            assert assets.public_assets(db, [sid])[sid] == {}
            rows[0].mime, rows[0].width = "image/svg+xml", 32
            db.commit()
            assert assets.public_assets(db, [sid])[sid]["icon"]["url"] == "https://fixture.example/tiny.png"
        finally:
            for r in rows:
                db.delete(r)
            db.commit()
