"""Canonical dataset integrity: deduplication and merges, preserved links and relationships, evidence-only verification,
durable administrator edits, idempotent rebuilds, pagination, the add-a-source workflow and data-quality reporting.
All records are FIXTURE data on *.fixture.example hosts."""
from __future__ import annotations

import pytest
from sqlalchemy import func, select

from app.database.session import SessionLocal
from app.models import (Component, DesignSystem, DuplicateGroup, IdentityLink, Job, Source, StorybookProject, SystemAlias,
                        SystemResource)
from app.services import ingest, jobs as jobsvc
from app.services import resources as ressvc
from app.services.build import run_build

BASE = {"secondary_categories": [], "tags": [], "relationships": [], "notes": ["FIXTURE"], "frameworks": ["React"], "technologies": [],
        "confidence": "medium", "verification_status": "unverified", "source_status": "third_party", "extraction_method": "html", "source_version": None}


def sysrec(src: str, slug: str, name: str, org: str | None = None, docs: str | None = None, repo: str | None = None, sb: str | None = None,
           figma: str | None = None) -> dict:
    return {**BASE, "source_id": src, "record_id": f"sys:{src.lower()}:{slug}", "record_type": "system", "title": name, "summary": f"FIXTURE {name}",
            "primary_category": "C12", "source_url": f"https://directory.fixture.example/{slug}", "organization": org, "design_system": name,
            "repository_url": repo,
            "normalized_content": {"name": name, "organization": org, "documentation_url": docs, "repository_url": repo, "storybook_url": sb,
                                   "design_resource_url": figma, "source_attributes": {}}}


def comprec(src: str, slug: str, name: str, system_record: str) -> dict:
    return {**BASE, "source_id": src, "record_id": f"cmp:{src.lower()}:{slug}", "record_type": "component", "title": name, "primary_category": "C05",
            "source_url": f"https://directory.fixture.example/c/{slug}", "organization": None, "design_system": None,
            "relationships": [{"type": "documented_by_system", "target": system_record}],
            "normalized_content": {"component_name": name, "library": None, "detail_level": "doc"}}


def _source(s, key: str, **kw) -> Source:
    src = s.scalar(select(Source).where(Source.key == key))
    if not src:
        src = Source(key=key, name=f"FIXTURE {key}", url=f"https://{key.lower()}.fixture.example/", canonical_url=f"https://{key.lower()}.fixture.example/",
                     domain=f"{key.lower()}.fixture.example", source_type="directory", adapter="generic", origin=kw.pop("origin", "user"), **kw)
        s.add(src)
        s.flush()
    return src


def _ingest(key: str, records: list[dict], **kw) -> None:
    with SessionLocal() as s:
        src = _source(s, key, **kw)
        job = jobsvc.enqueue(s, "crawl", source_id=src.id, params={"fixture": True})
        ingest.ingest(s, src, job.id, {"records": records, "coverage": {"crawl_status": "inspected", "errors": [], "limitations": []}})
        jobsvc.finish(s, job.id, "succeeded")
        s.commit()


def _build() -> dict:
    with SessionLocal() as s:
        out = run_build(s, None)
        s.commit()
        return out


def _sys(key: str) -> DesignSystem | None:
    with SessionLocal() as s:
        return s.scalar(select(DesignSystem).where(DesignSystem.key == key))


def _key_for(name: str, org: str | None) -> str:
    with SessionLocal() as s:
        return s.scalar(select(DesignSystem.key).where(DesignSystem.name == name, DesignSystem.organization.is_(None) if org is None
                                                          else DesignSystem.organization == org))


@pytest.fixture(scope="module")
def kb(built_kb):
    _ingest("FX2", [
        sysrec("FX2", "alpha", "Alpha", "Acme", docs="https://alpha.fixture.example/", repo="https://github.com/acme/alpha",
               sb="https://alpha-storybook.fixture.example/", figma="https://www.figma.com/@acme"),
        sysrec("FX2", "alpha-stub", "Alpha"),
        comprec("FX2", "alpha-button", "Button", "sys:fx2:alpha-stub"),
        sysrec("FX2", "beta", "Beta UI", "Betacorp", docs="https://beta.fixture.example/docs", figma="https://www.figma.com/file/AbC123/beta-kit"),
        sysrec("FX2", "canvas-a", "Canvas", "Workday Fixture", docs="https://canvas-a.fixture.example/"),
        sysrec("FX2", "canvas-b", "Canvas", "HubSpot Fixture", docs="https://canvas-b.fixture.example/"),
    ])
    _ingest("FX3", [sysrec("FX3", "alpha", "Alpha", "Acme", docs="https://alpha.fixture.example/", repo="https://github.com/acme/alpha")])
    _build()
    return {"alpha": _key_for("Alpha", "Acme"), "stub": _key_for("Alpha", None), "beta": _key_for("Beta UI", "Betacorp")}


def test_same_site_listings_consolidate_into_one_system_with_all_sources(kb):
    a = _sys(kb["alpha"])
    assert a is not None and a.source_keys == ["FX2", "FX3"]
    with SessionLocal() as s:
        assert s.scalar(select(func.count()).select_from(DesignSystem).where(DesignSystem.name == "Alpha", DesignSystem.organization == "Acme")) == 1
        site = s.scalar(select(SystemResource).where(SystemResource.system_key == kb["alpha"], SystemResource.resource_type == "official_website"))
        assert site.source_keys == ["FX2", "FX3"]  # both directories' attribution is kept on the link


def test_links_are_typed_and_figma_is_never_guessed(kb):
    with SessionLocal() as s:
        alpha = {(r.resource_type, r.canonical_url) for r in s.scalars(select(SystemResource).where(SystemResource.system_key == kb["alpha"]))}
        assert ("github_repository", "https://github.com/acme/alpha") in alpha
        assert ("storybook", "https://alpha-storybook.fixture.example/") in alpha
        # a Figma profile page is not a design file: kept, but as an additional resource
        assert not any(t == "figma_file" for t, _ in alpha)
        assert ("additional_resource", "https://www.figma.com/@acme") in alpha
        beta = s.scalars(select(SystemResource).where(SystemResource.system_key == kb["beta"])).all()
        assert {r.resource_type for r in beta} >= {"official_documentation", "figma_file"}
        for r in s.scalars(select(SystemResource).where(SystemResource.resource_type == "figma_file")):
            assert ressvc.FIGMA_FILE.match(r.url), r.url
        # directory listings alone never mark a link verified
        assert all(r.verification_status == "unverified" for r in beta)


def test_name_collisions_go_to_review_never_auto_merged(kb):
    with SessionLocal() as s:
        keys = set(s.scalars(select(DuplicateGroup.key).where(DuplicateGroup.review_status == "open")))
        assert "possible_duplicate_system:name:alpha" in keys and "possible_duplicate_system:name:canvas" in keys
        assert s.scalar(select(func.count()).select_from(DesignSystem).where(DesignSystem.name == "Canvas")) == 2
    assert _sys(kb["stub"]) is not None


def test_resolver_keeps_same_name_systems_of_different_organizations_apart():
    from app.services.review_resolver import _pair
    page = lambda url: {"url": url, "final_url": url, "ok": True, "status": 200, "outbound": []}  # noqa: E731
    a = {"key": "dsys:a", "name": "Canvas", "organization": "Workday", "urls": {"docs": "https://a.example/"}, "pages": {"docs": page("https://a.example/")},
         "sources": ["S1"], "has_site": True}
    b = {"key": "dsys:b", "name": "Canvas", "organization": "HubSpot", "urls": {"docs": "https://b.example/"}, "pages": {"docs": page("https://b.example/")},
         "sources": ["S2"], "has_site": True}
    decision, _, _, _ = _pair(a, b)
    assert decision == "distinct_system_confirmed"
    stub = {"key": "dsys:c", "name": "Components", "organization": None, "urls": {}, "pages": {}, "sources": ["S3"], "has_site": False}
    assert _pair(stub, a)[0] != "duplicate_confirmed"  # a generic-named stub is never merged into another organization's system


def test_confirmed_merge_preserves_ids_links_and_relationships(client, as_admin, kb):
    stub = _sys(kb["stub"])
    with SessionLocal() as s:
        before = s.scalar(select(func.count()).select_from(SystemResource).where(SystemResource.system_key == kb["alpha"]))
        assert s.scalar(select(Component.system_id).where(Component.name == "Button", Component.system_id == stub.id)) == stub.id
        s.add(IdentityLink(from_key=kb["stub"], to_key=kb["alpha"], relation="same_as", evidence=[{"type": "FIXTURE decision"}]))
        s.commit()
    _build()
    assert _sys(kb["stub"]) is None
    alpha = _sys(kb["alpha"])
    with SessionLocal() as s:
        alias = s.get(SystemAlias, kb["stub"])
        assert alias.alias_id == stub.id and alias.canonical_key == kb["alpha"]
        assert s.scalar(select(Component.system_id).where(Component.name == "Button", Component.source_id == alpha_source_id(s))) == alpha.id
        after = s.scalar(select(func.count()).select_from(SystemResource).where(SystemResource.system_key == kb["alpha"]))
        assert after >= before
    r = client.get(f"/api/v1/design-systems/{stub.id}", headers=as_admin).json()["data"]
    assert r["id"] == alpha.id and r["requested_alias"]["id"] == stub.id
    assert any(a["key"] == kb["stub"] for a in r["merged_aliases"])


def alpha_source_id(s) -> int:
    return s.scalar(select(Source.id).where(Source.key == "FX2"))


def test_rebuild_is_idempotent(kb):
    with SessionLocal() as s:
        snap = lambda: (s.scalar(select(func.count()).select_from(DesignSystem)), s.scalar(select(func.count()).select_from(SystemResource)),  # noqa: E731
                        s.scalar(select(func.count()).select_from(SystemAlias)), s.scalar(select(func.count()).select_from(Component)))
        first = snap()
    _build()
    with SessionLocal() as s:
        snap2 = (s.scalar(select(func.count()).select_from(DesignSystem)), s.scalar(select(func.count()).select_from(SystemResource)),
                 s.scalar(select(func.count()).select_from(SystemAlias)), s.scalar(select(func.count()).select_from(Component)))
    assert first == snap2


def test_admin_edits_and_link_decisions_survive_rebuilds(client, as_admin, kb):
    beta = _sys(kb["beta"])
    r = client.patch(f"/api/v1/design-systems/{beta.id}", headers=as_admin, json={"description": "FIXTURE curated description", "platforms": ["Web"]})
    assert r.status_code == 200 and r.json()["data"]["description"] == "FIXTURE curated description"
    add = client.post(f"/api/v1/design-systems/{beta.id}/resources", headers=as_admin,
                      json={"resource_type": "github_repository", "url": "https://github.com/betacorp/beta-ui", "verification_status": "verified"})
    assert add.status_code == 201
    figma = next(x for x in r.json()["data"]["resources"] if x["resource_type"] == "figma_file")
    assert client.patch(f"/api/v1/resources/{figma['id']}", headers=as_admin, json={"verification_status": "invalid"}).status_code == 200
    _build()
    d = client.get(f"/api/v1/design-systems/{beta.id}", headers=as_admin).json()["data"]
    assert d["description"] == "FIXTURE curated description" and d["platforms"] == ["Web"]
    res = {x["url"]: x for x in d["resources"]}
    assert res["https://github.com/betacorp/beta-ui"]["verification_status"] == "verified"
    assert res["https://www.figma.com/file/AbC123/beta-kit"]["verification_status"] == "invalid"
    # derived links cannot be deleted (provenance); manual ones can
    assert client.delete(f"/api/v1/resources/{figma['id']}", headers=as_admin).status_code == 409
    assert client.delete(f"/api/v1/resources/{add.json()['data']['id']}", headers=as_admin).status_code == 204


def test_bad_resource_values_are_rejected(client, as_admin, kb):
    beta = _sys(kb["beta"])
    url = f"/api/v1/design-systems/{beta.id}/resources"
    assert client.post(url, headers=as_admin, json={"resource_type": "figma_file", "url": "https://www.figma.com/community"}).status_code == 409
    assert client.post(url, headers=as_admin, json={"resource_type": "github_repository", "url": "https://github.com/features"}).status_code == 409
    assert client.post(url, headers=as_admin, json={"resource_type": "official_website", "url": "javascript:alert(1)"}).status_code == 422


def test_every_system_is_reachable_through_pagination(client, as_admin, kb):
    with SessionLocal() as s:
        total = s.scalar(select(func.count()).select_from(DesignSystem))
    seen, page = set(), 1
    while True:
        r = client.get("/api/v1/design-systems", headers=as_admin, params={"page": page, "page_size": 2}).json()
        seen |= {x["id"] for x in r["data"]}
        if page >= r["meta"]["total_pages"]:
            break
        page += 1
    assert r["meta"]["total_items"] == total == len(seen) and page > 1


def test_catalog_returns_only_existing_links_and_filters_server_side(client, as_admin, kb):
    rows = client.get("/api/v1/design-systems", headers=as_admin, params={"q": "Beta UI"}).json()["data"]
    beta = next(x for x in rows if x["key"] == kb["beta"])
    assert all(link["url"] for link in beta["links"])
    assert {link["type"] for link in beta["links"]} <= set(ressvc.TYPE_ORDER)
    got = client.get("/api/v1/design-systems", headers=as_admin, params={"resource": "github_repository", "page_size": 100}).json()
    keys = {x["key"] for x in got["data"]}
    assert kb["alpha"] in keys and kb["beta"] not in keys  # beta's only repository link (manual) was removed above
    missing = client.get("/api/v1/design-systems", headers=as_admin, params={"missing_resource": "official", "page_size": 100}).json()
    assert kb["alpha"] not in {x["key"] for x in missing["data"]}
    assert client.get("/api/v1/design-systems", headers=as_admin, params={"component": "Button", "page_size": 100}).json()["meta"]["total_items"] >= 1


def test_intake_checks_for_existing_system_before_creating(client, as_admin, kb):
    alpha = _sys(kb["alpha"])
    chk = client.post("/api/v1/intake/check", headers=as_admin, json={"url": "https://alpha.fixture.example/components", "name": "Alpha"}).json()["data"]
    assert any(c["system_id"] == alpha.id and c["match"] == "same_site" for c in chk["candidates"])
    assert chk["suggested_type"] == "official_documentation"
    dup = client.post("/api/v1/intake", headers=as_admin, json={"url": "https://alpha.fixture.example/components", "resource_type": "official_documentation",
                                                                  "new_system": {"name": "Alpha"}, "crawl": False})
    assert dup.status_code == 409
    # forcing "separate" still refuses: the documentation site already belongs to a canonical system
    forced = client.post("/api/v1/intake", headers=as_admin, json={"url": "https://alpha.fixture.example/components", "resource_type": "official_documentation",
                                                                     "new_system": {"name": "Alpha"}, "separate_from": [alpha.id], "crawl": False})
    assert forced.status_code == 409
    attach = client.post("/api/v1/intake", headers=as_admin, json={"url": "https://www.figma.com/file/XyZ789/alpha-kit", "resource_type": "figma_file",
                                                                     "system_id": alpha.id, "verified": True, "crawl": False})
    assert attach.status_code == 201 and attach.json()["data"]["resource"]["verification_status"] == "verified"


def test_intake_new_system_queues_crawl_build_verify_once(client, as_admin, kb):
    body = {"url": "https://gamma.fixture.example/", "resource_type": "official_website", "new_system": {"name": "Gamma", "organization": "Gammaco"}, "crawl": True}
    r = client.post("/api/v1/intake", headers=as_admin, json=body)
    assert r.status_code == 201
    out = r.json()["data"]
    assert out["system_key"] == "dsys:gamma-fixture-example" and len(out["job_ids"]) == 3
    with SessionLocal() as s:
        kinds = [s.get(Job, j).kind for j in out["job_ids"]]
        assert kinds == ["crawl", "build", "verify_resources"]
        src = s.get(Source, out["source_id"])
        assert src.system_key == "dsys:gamma-fixture-example" and src.origin == "official"
        for j in out["job_ids"]:  # don't let the fixture jobs run against the network
            jobsvc.cancel(s, j)
        s.commit()
    again = client.post("/api/v1/intake", headers=as_admin, json=body)
    assert again.status_code == 409  # the same URL is now recorded; a second submission cannot create a duplicate


def test_source_bound_to_a_system_cannot_spawn_a_duplicate(kb):
    alpha_key = kb["alpha"]
    _ingest("OFX", [sysrec("OFX", "alpha-moved", "Alpha", "Acme", docs="https://alpha-new-home.fixture.example/")], origin="official", system_key=alpha_key)
    _build()
    with SessionLocal() as s:
        assert s.scalar(select(func.count()).select_from(DesignSystem).where(DesignSystem.key.like("%alpha-new-home%"))) == 0
        assert "OFX" in s.scalar(select(DesignSystem.source_keys).where(DesignSystem.key == alpha_key))


def test_storybook_projects_follow_their_showcase_listing(kb):
    with SessionLocal() as s:
        s.add(StorybookProject(slug="fx-beta", title="Beta UI", storybook_url="https://beta-sb.fixture.example/", status="no_public_index",
                               showcase_record_key="sys:fx2:beta", system_key=None))
        s.commit()
    _build()
    with SessionLocal() as s:
        assert s.scalar(select(StorybookProject.system_key).where(StorybookProject.slug == "fx-beta")) == kb["beta"]


def test_quality_distinguishes_absent_figma_from_unchecked(client, as_admin, kb):
    from datetime import datetime, timezone
    with SessionLocal() as s:
        site = s.scalar(select(SystemResource).where(SystemResource.system_key == kb["alpha"], SystemResource.is_primary.is_(True),
                                                     SystemResource.resource_type == "official_website"))
        s.query(SystemResource).filter(SystemResource.system_key == kb["alpha"], SystemResource.resource_type == "figma_file").delete()
        site.last_checked_at, site.http_status = datetime.now(timezone.utc), 200
        s.commit()
    alpha = _sys(kb["alpha"])
    nf = client.get("/api/v1/quality/issues", headers=as_admin, params={"kind": "figma_not_found", "page_size": 100}).json()["data"]
    un = client.get("/api/v1/quality/issues", headers=as_admin, params={"kind": "figma_unchecked", "page_size": 100}).json()["data"]
    assert alpha.id in {x["id"] for x in nf} and alpha.id not in {x["id"] for x in un}
    summary = client.get("/api/v1/quality", headers=as_admin).json()["data"]
    assert set(summary["counts"]) >= {"duplicate_candidates", "missing_official_url", "invalid_links", "orphaned_records", "extraction_failures"}


class _Resp:
    def __init__(self, url: str, html: str, status: int = 200):
        self.url = self.final_url = url
        self.status = status
        self.content = html.encode()

    @property
    def text(self) -> str:
        return self.content.decode()


def test_verifier_confirms_links_from_the_official_page_and_ignores_host_chrome(kb):
    from datetime import datetime, timezone
    html = """<a href="https://github.com/acme/alpha">Code</a> <a href="https://github.com/security/advanced-security">GH chrome</a>
              <a href="https://github.com/acme/alpha">again</a> <a href="https://www.figma.com/@acme">profile</a>
              <a href="https://www.figma.com/community/file/1234567890/alpha-ui-kit">Kit</a> <a href="https://twitter.com/acme">x</a>"""
    with SessionLocal() as s:
        site = s.scalar(select(SystemResource).where(SystemResource.system_key == kb["alpha"], SystemResource.resource_type == "official_website",
                                                     SystemResource.is_primary.is_(True)))
        summary = {k: 0 for k in ("pages_ok", "pages_invalid", "pages_unreachable", "repos_verified", "repos_discovered", "figma_found", "storybooks_found")}
        ressvc._check_one(s, kb["alpha"], site.id, _Resp(site.url, html), datetime.now(timezone.utc), summary)
        s.commit()
        res = {(r.resource_type, r.canonical_url): r for r in s.scalars(select(SystemResource).where(SystemResource.system_key == kb["alpha"]))}
    assert res[("github_repository", "https://github.com/acme/alpha")].verification_status == "verified"
    assert ("github_repository", "https://github.com/security/advanced-security") not in res
    fig = res[("figma_file", "https://www.figma.com/community/file/1234567890/alpha-ui-kit")]
    assert fig.verification_status == "verified" and fig.origin == "official_site" and fig.access_note
    assert not any(t == "figma_file" and "@acme" in u for t, u in res)


def test_unreachable_official_page_is_marked_invalid_not_deleted(kb):
    from datetime import datetime, timezone
    with SessionLocal() as s:
        beta_doc = s.scalar(select(SystemResource).where(SystemResource.system_key == kb["beta"], SystemResource.resource_type == "official_documentation"))
        ressvc._check_one(s, kb["beta"], beta_doc.id, _Resp(beta_doc.url, "", status=404), datetime.now(timezone.utc), {"pages_invalid": 0})
        s.commit()
        s.refresh(beta_doc)
        assert beta_doc.verification_status == "invalid" and beta_doc.http_status == 404
    _build()  # a rebuild must not resurrect it as unverified
    with SessionLocal() as s:
        assert s.get(SystemResource, beta_doc.id).verification_status == "invalid"


@pytest.mark.parametrize("repo,name,org,site,expected", [
    ("https://github.com/alphagov/accessible-autocomplete", "W3C Design System", None, "https://design-system.w3.org/", False),  # dependency credit
    ("https://github.com/websemantics/awesome-ant-design", "Ant Design", "Ant Financial", "https://ant.design/", False),  # community list
    ("https://github.com/sindresorhus/grunt-sass", "Solid", "BuzzFeed", "https://www.buzzfeed.com/static-assets/solid-docs/", False),
    ("https://github.com/adjust/atlas", "Adjust Atlas", "Adjust", "https://atlas.adeven.com/", True),
    ("https://github.com/nl-design-system/utrecht", "NL Design System", None, "https://nldesignsystem.nl/", True),
    ("https://github.com/centrica-engineering/nucleus-docs", "British Gas Nucleus", "British Gas", "https://britishgas.design/", True),
])
def test_repository_ownership_rule(repo, name, org, site, expected):
    assert ressvc.repo_owned_by_system(repo, name, org, site, set()) is expected


def test_figma_links_canonicalize_without_view_parameters():
    a = ressvc.canon("figma_file", "https://www.figma.com/proto/3ptKrYEYpHR2rpLHiG9coQ/Brand?node-id=746-29290&scaling=contain")
    b = ressvc.canon("figma_file", "https://figma.com/proto/3ptKrYEYpHR2rpLHiG9coQ/Brand?node-id=890-53396")
    assert a == b == "https://www.figma.com/proto/3ptKrYEYpHR2rpLHiG9coQ/Brand"


def test_admin_duplicate_decision_merges_and_records_evidence(client, as_admin, kb):
    with SessionLocal() as s:
        item = s.scalar(select(DuplicateGroup).where(DuplicateGroup.key == "possible_duplicate_system:name:canvas"))
        keys = [e["system_id"] for e in item.details["entities"]]
    assert client.post(f"/api/v1/review-queue/{item.id}/decide", headers=as_admin, json={"decision": "merge", "canonical_key": "dsys:nope", "note": "x y z"}).status_code == 409
    r = client.post(f"/api/v1/review-queue/{item.id}/decide", headers=as_admin, json={"decision": "distinct", "note": "Different publishers and sites"})
    assert r.status_code == 200 and r.json()["data"]["review_status"] == "resolved"
    with SessionLocal() as s:
        assert s.scalar(select(func.count()).select_from(IdentityLink).where(IdentityLink.relation == "distinct_from",
                                                                              IdentityLink.from_key.in_(keys), IdentityLink.to_key.in_(keys))) == 1
        for j in s.scalars(select(Job).where(Job.kind == "build", Job.status == "queued")):  # keep the fixture DB deterministic
            jobsvc.cancel(s, j.id)
        s.commit()
    _build()
    with SessionLocal() as s:  # decided pairs are not re-queued
        assert s.scalar(select(DuplicateGroup.review_status).where(DuplicateGroup.key == "possible_duplicate_system:name:canvas")) == "resolved"


def test_repository_named_after_another_product_is_not_the_systems_repository():
    assert not ressvc.repo_name_matches("https://github.com/shopify/remote-dom", "Polaris", ["Shopify Polaris"], "Shopify")
    assert not ressvc.repo_name_matches("https://github.com/shopify/shopify-cli", "Polaris", ["Shopify Polaris"], "Shopify")
    assert ressvc.repo_name_matches("https://github.com/shopify/polaris", "Polaris", ["Shopify Polaris"], "Shopify")
    assert ressvc.repo_name_matches("https://github.com/reshaped-ui/reshaped", "Reshaped", [], "Reshaped")  # named after its company
