# GitHub API Configuration & Optimization Guide

This guide details how to securely configure GitHub API access for the Design Systems Research Platform (DSRP) and how the platform optimizes API consumption.

---

## 1. Why Configure a GitHub Token?

* **Unauthenticated Rate Limit:** 60 requests per hour per IP.
* **Authenticated Rate Limit:** 5,000 requests per hour with a Personal Access Token (PAT) or GitHub App token.
* **Impact on Research:** Verifying repository ownership, licenses (SPDX), default branches, and push activity for hundreds of open-source design systems requires significant quota headroom.

---

## 2. Generating a Least-Privileged Credential

To follow the principle of least privilege, **never** generate a token with full account or admin scopes.

### Recommended: Fine-Grained Personal Access Token (PAT)
1. Navigate to **GitHub → Settings → Developer Settings → Personal Access Tokens → Fine-grained tokens**.
2. Click **Generate new token**.
3. **Repository access:** Select **Public Repositories (read-only)**.
4. **Permissions:**
   * Under **Repository permissions**, ensure only **Contents** (read-only) and **Metadata** (read-only, default) are selected.
   * Do **not** grant any Organization, Account, or Admin permissions.
5. Set an appropriate expiration period (e.g., 90 days).
6. Copy the generated token (`github_pat_...`).

---

## 3. Configuring the Token in DSRP

### Option A: Local Development (`backend/.env`)
Add the token to your local, git-ignored `backend/.env` file:
```env
GITHUB_TOKEN=github_pat_your_token_here
```

### Option B: Process Environment
Export the variable in your shell or container orchestration environment:
```bash
export GITHUB_TOKEN="github_pat_your_token_here"
```

### Option C: Production Secret Store
In Kubernetes, Docker Swarm, or AWS/GCP deployments, mount `GITHUB_TOKEN` as an environment secret into the backend API and worker pods.

> [!WARNING]
> Never commit `GITHUB_TOKEN` to git, never paste it in pull requests, and never include it in frontend environment variables. The backend Pydantic settings mask this variable as a `SecretStr`.

---

## 4. Verification & Diagnostics

Once configured, verify the status through the authenticated admin endpoint:
```bash
curl -X GET http://localhost:8000/api/v1/admin/integrations/github \
  -H "Authorization: Bearer <your_session_token>"
```

Expected response structure:
```json
{
  "data": {
    "checked_at": "2026-10-21T11:42:02Z",
    "token_configured": true,
    "mode": "authenticated",
    "rate_limits": {
      "core": {
        "limit": 5000,
        "remaining": 4998,
        "reset_at": "2026-10-21T12:42:02Z"
      }
    }
  }
}
```

---

## 5. Architectural Optimizations for Quota Conservation

1. **Zero-Quota Raw Content Fetching:**
   CSF source code (Storybook component variants) and repository READMEs are retrieved via `raw.githubusercontent.com`. This consumes **0 REST API requests**.
2. **Conditional HTTP Requests:**
   All API requests store ETags and send `If-None-Match`. Unchanged responses return HTTP 304, consuming no rate-limit quota.
3. **Pre-Call Quota Gating (`_gate()`):**
   When remaining quota hits 0, the adapter pauses execution if reset is within 90 seconds, preventing secondary rate-limit penalties.
4. **Link-Header Pagination:**
   File tree and release listings follow RFC 5988 `Link: rel="next"` headers with a bounded page size (`per_page=100`).
