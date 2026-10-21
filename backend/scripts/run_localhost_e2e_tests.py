#!/usr/bin/env python3
"""Comprehensive localhost end-to-end integration test runner for DSRP.
Tests both frontend (localhost:3000) and backend (localhost:8000).
"""
import sys
import json
import re
import urllib.request
import urllib.error
import http.cookiejar
from pathlib import Path

BASE_FE = "http://localhost:3000"
BASE_BE = "http://localhost:8000"
STORAGE_OUTBOX = Path("backend/storage/outbox")

results = []

def record(name: str, passed: bool, detail: str = ""):
    status = "PASS" if passed else "FAIL"
    results.append((name, status, detail))
    print(f"[{status}] {name}{': ' + detail if detail else ''}")
    if not passed:
        print(f"  FAILED DETAILS: {detail}", file=sys.stderr)

def test_security_headers_and_redirects():
    print("\n--- TEST SUITE 1: Security Headers & Edge Protection ---")
    
    # 1. Unauthenticated request to / should redirect to /platform/login
    req = urllib.request.Request(f"{BASE_FE}/", headers={"User-Agent": "DSRP-Tester"})
    try:
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
        # Prevent auto-redirect to inspect 307
        class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
            def http_error_302(self, req, fp, code, msg, headers):
                return fp
            http_error_301 = http_error_303 = http_error_307 = http_error_302
        
        nr_opener = urllib.request.build_opener(NoRedirectHandler)
        res = nr_opener.open(req)
        loc = res.headers.get("Location", "")
        passed = res.status in (302, 307) and "/platform/login" in loc
        x_frame = res.headers.get("X-Frame-Options", "")
        nosniff = res.headers.get("X-Content-Type-Options", "")
        robots = res.headers.get("X-Robots-Tag", "")
        
        record("Unauthenticated / redirects to /platform/login", passed, f"Status {res.status}, Location: {loc}")
        record("Edge Security Header: X-Frame-Options: DENY", x_frame == "DENY", f"Value: {x_frame}")
        record("Edge Security Header: X-Content-Type-Options: nosniff", nosniff == "nosniff", f"Value: {nosniff}")
        record("Edge Security Header: X-Robots-Tag: noindex", "noindex" in robots, f"Value: {robots}")
    except Exception as e:
        record("Unauthenticated / redirect", False, str(e))

    # 2. Public access to /platform/login should succeed
    try:
        res = urllib.request.urlopen(f"{BASE_FE}/platform/login")
        body = res.read().decode("utf-8")
        record("Public page /platform/login accessible (200 OK)", res.status == 200 and "Sign in" in body)
    except Exception as e:
        record("Public page /platform/login accessible", False, str(e))

    # 3. Public access to /platform/invite should succeed
    try:
        res = urllib.request.urlopen(f"{BASE_FE}/platform/invite")
        record("Public page /platform/invite accessible (200 OK)", res.status == 200)
    except Exception as e:
        record("Public page /platform/invite accessible", False, str(e))

    # 4. Anonymous access to private API (/api/v1/systems) must be rejected with 401
    try:
        urllib.request.urlopen(f"{BASE_FE}/api/v1/systems")
        record("Anonymous API request rejected with 401", False, "Expected HTTP 401, got 200")
    except urllib.error.HTTPError as e:
        record("Anonymous API request rejected with 401", e.code == 401, f"Received HTTP {e.code}")
    except Exception as e:
        record("Anonymous API request rejected with 401", False, str(e))

def test_admin_authentication():
    print("\n--- TEST SUITE 2: Admin Authentication ---")
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    login_data = json.dumps({"email": "ravi.kumar@graphikx.in", "password": "Ravi@4681"}).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_FE}/api/v1/auth/login",
        data=login_data,
        headers={"Content-Type": "application/json", "User-Agent": "DSRP-Tester"}
    )

    try:
        res = opener.open(req)
        body = json.loads(res.read().decode("utf-8"))
        passed = res.status == 200 and body.get("data", {}).get("user", {}).get("role") == "admin"
        cookies = {c.name: c.value for c in cj}
        has_session = "dsrp_session" in cookies
        has_csrf = "dsrp_csrf" in cookies

        record("Admin login (ravi.kumar@graphikx.in)", passed, f"User: {body.get('data', {}).get('user', {}).get('email')}, Role: {body.get('data', {}).get('user', {}).get('role')}")
        record("Session cookie (dsrp_session) issued", has_session, f"Length: {len(cookies.get('dsrp_session', ''))}")
        record("CSRF cookie (dsrp_csrf) issued", has_csrf, f"Value: {cookies.get('dsrp_csrf', '')}")

        # Verify /api/v1/auth/me
        me_req = urllib.request.Request(f"{BASE_FE}/api/v1/auth/me", headers={"User-Agent": "DSRP-Tester"})
        me_res = opener.open(me_req)
        me_body = json.loads(me_res.read().decode("utf-8"))
        me_passed = me_res.status == 200 and me_body.get("data", {}).get("id") == body["data"]["user"]["id"]
        record("Verify authenticated identity (/auth/me)", me_passed, f"ID: {me_body.get('data', {}).get('id')}")

        return opener, cookies
    except Exception as e:
        record("Admin login", False, str(e))
        return None, None

def test_platform_data_apis(opener):
    print("\n--- TEST SUITE 3: Full Platform Data APIs & Truthfulness ---")
    if not opener:
        record("Platform Data APIs", False, "Skipped due to login failure")
        return

    # 1. Dashboard summary
    try:
        res = opener.open(f"{BASE_FE}/api/v1/dashboard/summary")
        data = json.loads(res.read().decode("utf-8"))["data"]
        
        record("Live metric: Design systems count", data.get("design_systems", 0) >= 470, f"Found {data.get('design_systems')}")
        record("Live metric: Components count", data.get("components", 0) >= 3300, f"Found {data.get('components')}")
        record("Live metric: Storybook projects count", data.get("storybook_projects", 0) == 103, f"Found {data.get('storybook_projects')}")
        record("Live metric: Storybook stories count", data.get("storybook_stories", 0) == 17600, f"Found {data.get('storybook_stories')}")
        record("Live metric: Storybook variants count", data.get("storybook_variants", 0) == 12150, f"Found {data.get('storybook_variants')}")
        record("Live metric: Attribute evidence count", data.get("attribute_evidence", 0) == 312, f"Found {data.get('attribute_evidence')}")
    except Exception as e:
        record("Dashboard summary API", False, str(e))

    # 2. Design systems list & official docs url
    try:
        res = opener.open(f"{BASE_FE}/api/v1/systems?page_size=5")
        body = json.loads(res.read().decode("utf-8"))
        items = body.get("data", [])
        has_docs = any(i.get("official_docs_url") for i in items)
        record("Systems list returns official_docs_url", has_docs, f"Sample items: {len(items)}")
        
        # Test evidence endpoint for system 1
        sys_id = items[0]["id"]
        ev_res = opener.open(f"{BASE_FE}/api/v1/systems/{sys_id}/evidence")
        ev_body = json.loads(ev_res.read().decode("utf-8"))
        record(f"System evidence endpoint (/systems/{sys_id}/evidence)", ev_res.status == 200, f"Evidence count: {ev_body.get('meta', {}).get('total_items')}")

        # Test storybook endpoint for system 1
        sb_res = opener.open(f"{BASE_FE}/api/v1/systems/{sys_id}/storybook")
        sb_body = json.loads(sb_res.read().decode("utf-8"))
        record(f"System storybook endpoint (/systems/{sys_id}/storybook)", sb_res.status == 200, f"Project: {sb_body.get('data', {}).get('title') if sb_body.get('data') else 'None'}")
    except Exception as e:
        record("Systems endpoints", False, str(e))

    # 3. Storybook explorer APIs
    try:
        proj_res = opener.open(f"{BASE_FE}/api/v1/storybook/projects?page_size=5")
        proj_body = json.loads(proj_res.read().decode("utf-8"))
        record("Storybook projects endpoint (/storybook/projects)", proj_body.get("meta", {}).get("total_items") == 103, f"Total: {proj_body.get('meta', {}).get('total_items')}")

        stories_res = opener.open(f"{BASE_FE}/api/v1/storybook/stories?page_size=5")
        stories_body = json.loads(stories_res.read().decode("utf-8"))
        record("Storybook stories endpoint (/storybook/stories)", stories_body.get("meta", {}).get("total_items") == 17600, f"Total: {stories_body.get('meta', {}).get('total_items')}")

        var_res = opener.open(f"{BASE_FE}/api/v1/storybook/variants?page_size=5")
        var_body = json.loads(var_res.read().decode("utf-8"))
        record("Storybook variants endpoint (/storybook/variants)", var_body.get("meta", {}).get("total_items") == 12150, f"Total: {var_body.get('meta', {}).get('total_items')}")
    except Exception as e:
        record("Storybook explorer APIs", False, str(e))

def test_invitation_lifecycle(admin_opener, admin_cookies):
    print("\n--- TEST SUITE 4: Invitation-Only Lifecycle ---")
    if not admin_opener:
        record("Invitation Lifecycle", False, "Skipped due to missing admin session")
        return

    csrf_token = admin_cookies.get("dsrp_csrf", "")
    target_email = "e2e.researcher@example.org"

    # 1. Admin issues invitation
    try:
        payload = json.dumps({"email": target_email, "role": "researcher", "ttl_hours": 48}).encode("utf-8")
        req = urllib.request.Request(
            f"{BASE_FE}/api/v1/admin/invitations",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "x-csrf-token": csrf_token,
                "User-Agent": "DSRP-Tester"
            }
        )
        res = admin_opener.open(req)
        inv_data = json.loads(res.read().decode("utf-8"))["data"]
        inv_id = inv_data["id"]
        record("Admin issues single-use invitation (POST /admin/invitations)", res.status == 201, f"Inv ID: {inv_id}, Recipient: {inv_data['email']}")

        # 2. Inspect development outbox for delivery file
        outbox_files = sorted(STORAGE_OUTBOX.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        latest_msg = None
        for p in outbox_files:
            try:
                data = json.loads(p.read_text())
                if data.get("to") == target_email:
                    latest_msg = data
                    break
            except Exception:
                continue

        record("Invitation email rendered to development outbox", latest_msg is not None, f"File: {p.name if latest_msg else 'not found'}")
        if not latest_msg:
            return

        inv_url = latest_msg.get("invitation_url", "")
        token_match = re.search(r"token=([A-Za-z0-9_-]+)", inv_url)
        token = token_match.group(1) if token_match else None
        record("Extracted cryptographically secure token from invitation fragment", token is not None, f"Token prefix: {token[:12] if token else ''}...")

        if not token:
            return

        # 3. Validate invitation token
        val_data = json.dumps({"token": token}).encode("utf-8")
        val_req = urllib.request.Request(
            f"{BASE_FE}/api/v1/auth/invitations/validate",
            data=val_data,
            headers={"Content-Type": "application/json"}
        )
        val_res = urllib.request.urlopen(val_req)
        val_body = json.loads(val_res.read().decode("utf-8"))["data"]
        record("Validate invitation token (/auth/invitations/validate)", val_body.get("role") == "researcher" and "e***@example.org" in val_body.get("email_hint"), f"Masked hint: {val_body.get('email_hint')}")

        # 4. Request 6-digit verification code
        code_req = urllib.request.Request(
            f"{BASE_FE}/api/v1/auth/invitations/send-code",
            data=val_data,
            headers={"Content-Type": "application/json"}
        )
        code_res = urllib.request.urlopen(code_req)
        record("Send 6-digit verification code (/auth/invitations/send-code)", code_res.status == 200)

        # 5. Extract verification code from second outbox email
        outbox_files = sorted(STORAGE_OUTBOX.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        code_msg = None
        for p in outbox_files:
            try:
                data = json.loads(p.read_text())
                if data.get("to") == target_email and "code" in data:
                    code_msg = data
                    break
            except Exception:
                continue

        vcode = code_msg.get("code") if code_msg else None
        record("Extracted 6-digit verification code from outbox", vcode is not None and len(vcode) == 6, f"Code: {vcode}")

        if not vcode:
            return

        # 6. Accept invitation and establish session
        new_cj = http.cookiejar.CookieJar()
        new_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(new_cj))
        accept_payload = json.dumps({
            "token": token,
            "code": vcode,
            "name": "Dr. Researcher",
            "password": "ResearcherPassword2026!"
        }).encode("utf-8")
        accept_req = urllib.request.Request(
            f"{BASE_FE}/api/v1/auth/invitations/accept",
            data=accept_payload,
            headers={"Content-Type": "application/json"}
        )
        accept_res = new_opener.open(accept_req)
        accept_body = json.loads(accept_res.read().decode("utf-8"))["data"]
        record("Accept invitation & create identity (/auth/invitations/accept)", accept_res.status == 200 and accept_body["user"]["email"] == target_email, f"User ID: {accept_body['user']['id']}")

        # 7. Verify replay protection: reusing the token must fail with 400
        try:
            urllib.request.urlopen(accept_req)
            record("Invitation replay protection (single-use)", False, "Replay was unexpectedly permitted")
        except urllib.error.HTTPError as e:
            record("Invitation replay protection (single-use)", e.code in (400, 404, 409), f"Replay rejected with HTTP {e.code}")
    except Exception as e:
        record("Invitation lifecycle", False, str(e))

def test_frontend_rendered_pages(opener):
    print("\n--- TEST SUITE 5: Frontend SSR / Client Rendering ---")
    if not opener:
        return

    pages = [
        ("/platform", "Dashboard"),
        ("/platform/storybook", "Storybook & component variants"),
        ("/platform/systems", "Design systems"),
        ("/platform/components", "Components"),
        ("/platform/admin", "Administration"),
    ]

    for path, title in pages:
        try:
            res = opener.open(f"{BASE_FE}{path}")
            body = res.read().decode("utf-8")
            passed = res.status == 200 and len(body) > 500
            record(f"Frontend view: {path}", passed, f"Status: {res.status}, Length: {len(body)} bytes")
        except Exception as e:
            record(f"Frontend view: {path}", False, str(e))

def main():
    print("=" * 60)
    print("DSRP PRODUCTION END-TO-END TEST SUITE (LOCALHOST)")
    print(f"Frontend: {BASE_FE} | Backend: {BASE_BE}")
    print("=" * 60)

    test_security_headers_and_redirects()
    opener, cookies = test_admin_authentication()
    test_platform_data_apis(opener)
    test_invitation_lifecycle(opener, cookies)
    test_frontend_rendered_pages(opener)

    print("\n" + "=" * 60)
    total = len(results)
    passed = sum(1 for _, s, _ in results if s == "PASS")
    failed = total - passed
    print(f"TEST SUMMARY: Total: {total} | Passed: {passed} | Failed: {failed}")
    print("=" * 60)

    if failed > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
