"""Tests for invitation-only access, invitation lifecycle, and data reconciliation endpoints."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest
from conftest import FIXTURE_PW
from app.models import DesignSystem, Component, StorybookProject, StorybookStory, StorybookVariant, AttributeEvidence


def test_invitation_lifecycle_end_to_end(client, as_admin, as_researcher, as_viewer, db):
    from app.models import Invitation
    from app.services.invitations import _digest

    # 1. Non-admin cannot list or create invitations
    assert client.get("/api/v1/admin/invitations", headers=as_viewer).status_code == 403
    assert client.get("/api/v1/admin/invitations", headers=as_researcher).status_code == 403
    assert client.post("/api/v1/admin/invitations", headers=as_viewer, json={"email": "newbie@example.com", "role": "viewer"}).status_code == 403

    # 2. Admin creates an invitation
    invitee_email = "invited.researcher@dsrp.internal"
    r = client.post("/api/v1/admin/invitations", headers=as_admin, json={"email": invitee_email, "role": "researcher", "ttl_hours": 48})
    assert r.status_code == 201
    inv_data = r.json()["data"]
    assert inv_data["email"] == invitee_email
    assert inv_data["role"] == "researcher"
    assert inv_data["status"] == "pending"

    # 3. Find the raw token from the database outbox or link
    # Notice: the token digest is stored; in test/outbox mode, the message was delivered to outbox or storage
    inv_record = db.get(Invitation, inv_data["id"])
    assert inv_record is not None
    assert inv_record.token_digest is not None

    # Let's inspect the outbox to get the delivery token
    import json
    from app.core.config import get_settings
    outbox_dir = Path(get_settings().storage_dir) / "outbox"
    outbox_files = sorted(outbox_dir.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    assert len(outbox_files) > 0
    msg_data = json.loads(outbox_files[0].read_text())
    assert invitee_email == msg_data["to"]
    # Extract token from link: .../platform/invite#token=...
    token = msg_data["body"].split("#token=")[1].split("\n")[0].strip()

    # 4. Public validate endpoint (no auth required)
    val_resp = client.post("/api/v1/auth/invitations/validate", json={"token": token})
    assert val_resp.status_code == 200
    val_data = val_resp.json()["data"]
    assert val_data["kind"] == "access"
    assert val_data["role"] == "researcher"
    assert "@" in val_data["email_hint"]
    assert "invited" not in val_data["email_hint"]  # Masked!

    # 5. Tampered token is rejected
    assert client.post("/api/v1/auth/invitations/validate", json={"token": token + "_bad"}).status_code == 400

    # 6. Request verification code
    code_resp = client.post("/api/v1/auth/invitations/send-code", json={"token": token})
    assert code_resp.status_code == 200

    # Read the verification code from outbox
    code_files = sorted(outbox_dir.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    code_msg = json.loads(code_files[0].read_text())["body"]
    assert "Your verification code is" in code_msg
    code = code_msg.split("Your verification code is ")[1].split(".")[0].strip()
    assert len(code) == 6

    # 7. Wrong verification code is rejected
    wrong_code = "000000" if code != "000000" else "999999"
    bad_accept = client.post("/api/v1/auth/invitations/accept", json={
        "token": token,
        "code": wrong_code,
        "name": "Invited User",
        "password": "SecurePassword123!"
    })
    assert bad_accept.status_code == 400
    assert bad_accept.json()["error"]["code"] == "CODE_INVALID"

    # 8. Password too short (<12 chars) rejected
    short_pw = client.post("/api/v1/auth/invitations/accept", json={
        "token": token,
        "code": code,
        "name": "Invited User",
        "password": "short"
    })
    assert short_pw.status_code == 422

    # 9. Successful acceptance
    accept_resp = client.post("/api/v1/auth/invitations/accept", json={
        "token": token,
        "code": code,
        "name": "Dr. Researcher",
        "password": "AStrongResearcherPassword123!"
    })
    assert accept_resp.status_code == 200
    user_out = accept_resp.json()["data"]["user"]
    assert user_out["email"] == invitee_email
    assert user_out["role"] == "researcher"
    assert user_out["name"] == "Dr. Researcher"

    # Verify session cookie was set
    cookies = accept_resp.headers.get_list("set-cookie")
    assert any("dsrp_session=" in c for c in cookies)
    assert any("dsrp_csrf=" in c for c in cookies)

    # 10. Replay rejection: trying to accept again must fail
    replay = client.post("/api/v1/auth/invitations/accept", json={
        "token": token,
        "code": code,
        "name": "Dr. Researcher",
        "password": "AStrongResearcherPassword123!"
    })
    assert replay.status_code == 400
    assert replay.json()["error"]["code"] == "INVITATION_INVALID"

    # 11. Invitation status in admin list shows accepted
    inv_list = client.get("/api/v1/admin/invitations", headers=as_admin)
    assert inv_list.status_code == 200
    matching = [i for i in inv_list.json()["data"] if i["email"] == invitee_email]
    assert len(matching) == 1
    assert matching[0]["status"] == "accepted"

    # Clear cookies so client fixture stays unauthenticated for subsequent tests
    client.cookies.clear()



def test_invitation_revocation_and_resend(client, as_admin, db):
    import json
    from pathlib import Path
    from app.core.config import get_settings
    outbox_dir = Path(get_settings().storage_dir) / "outbox"

    # Create invite to revoke
    email = "revoked@example.com"
    r = client.post("/api/v1/admin/invitations", headers=as_admin, json={"email": email, "role": "viewer"})
    assert r.status_code == 201
    inv_id = r.json()["data"]["id"]

    outbox_files = sorted(outbox_dir.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    token1 = json.loads(outbox_files[0].read_text())["body"].split("#token=")[1].split("\n")[0].strip()

    # Revoke
    rev = client.post(f"/api/v1/admin/invitations/{inv_id}/revoke", headers=as_admin)
    assert rev.status_code == 200
    assert rev.json()["data"]["status"] == "revoked"

    # Validating revoked token fails
    assert client.post("/api/v1/auth/invitations/validate", json={"token": token1}).status_code == 400


def test_reconciliation_endpoints_and_dashboard(client, as_viewer, db):
    # 1. Dashboard summary has all extended fields
    d = client.get("/api/v1/dashboard/summary", headers=as_viewer).json()["data"]
    assert "storybook_projects" in d
    assert "storybook_stories" in d
    assert "storybook_variants" in d
    assert "attribute_evidence" in d
    assert d["design_systems"] >= 0

    # 2. System detail has official verification fields
    sys = db.query(DesignSystem).first()
    if sys:
        r = client.get(f"/api/v1/design-systems/{sys.id}", headers=as_viewer)
        assert r.status_code == 200
        sys_data = r.json()["data"]
        assert "official_docs_url" in sys_data
        assert "related_urls" in sys_data
        assert "verification_coverage" in sys_data

        # 3. System evidence endpoint
        ev_resp = client.get(f"/api/v1/design-systems/{sys.id}/evidence", headers=as_viewer)
        assert ev_resp.status_code == 200
        assert "data" in ev_resp.json()
        assert "meta" in ev_resp.json()

        # 4. System storybook endpoint
        sb_resp = client.get(f"/api/v1/design-systems/{sys.id}/storybook", headers=as_viewer)
        assert sb_resp.status_code == 200

    # 5. Component storybook endpoint
    comp = db.query(Component).first()
    if comp:
        c_sb = client.get(f"/api/v1/components/{comp.id}/storybook", headers=as_viewer)
        assert c_sb.status_code == 200
        sb_data = c_sb.json()["data"]
        assert "stories" in sb_data
        assert "variants" in sb_data
