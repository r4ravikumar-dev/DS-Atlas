"""API exposes the reconciled fields (Storybook, evidence, verification coverage) for systems and components."""
from app.models import Component, DesignSystem


def test_reconciliation_endpoints_and_dashboard(client, as_admin, db):
    # 1. Dashboard summary has all extended fields
    d = client.get("/api/v1/dashboard/summary", headers=as_admin).json()["data"]
    assert "storybook_projects" in d
    assert "storybook_stories" in d
    assert "storybook_variants" in d
    assert "attribute_evidence" in d
    assert d["design_systems"] >= 0

    # 2. System detail has official verification fields
    sys = db.query(DesignSystem).first()
    if sys:
        r = client.get(f"/api/v1/design-systems/{sys.id}", headers=as_admin)
        assert r.status_code == 200
        sys_data = r.json()["data"]
        assert "official_docs_url" in sys_data
        assert "related_urls" in sys_data
        assert "verification_coverage" in sys_data

        # 3. System evidence endpoint
        ev_resp = client.get(f"/api/v1/design-systems/{sys.id}/evidence", headers=as_admin)
        assert ev_resp.status_code == 200
        assert "data" in ev_resp.json()
        assert "meta" in ev_resp.json()

        # 4. System storybook endpoint
        sb_resp = client.get(f"/api/v1/design-systems/{sys.id}/storybook", headers=as_admin)
        assert sb_resp.status_code == 200

    # 5. Component storybook endpoint
    comp = db.query(Component).first()
    if comp:
        c_sb = client.get(f"/api/v1/components/{comp.id}/storybook", headers=as_admin)
        assert c_sb.status_code == 200
        sb_data = c_sb.json()["data"]
        assert "stories" in sb_data
        assert "variants" in sb_data
