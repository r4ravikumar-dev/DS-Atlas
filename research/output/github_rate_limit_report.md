# GitHub API Integration, Authentication & Rate-Limit Optimization Report

**Generated:** 2026-10-21T11:43:18.714790+00:00  
**Platform:** Design Systems Research Platform (DSRP)  
**Configuration Status:** Mode: `unauthenticated` | Rate Limit: `51/60` remaining | Reset: `2026-10-21T12:12:06+00:00`

## Executive Summary

| Parameter | Current Value | Optimal Authenticated Target |
|---|---|---|
| **Token Configuration** | `False` (unauthenticated) | `true` (via `GITHUB_TOKEN`) |
| **Core Rate Limit Quota** | **60 requests / hour** | **5,000 requests / hour** |
| **Remaining Core Quota** | **51 requests** | Up to 5,000 requests |
| **Search API Limit** | 10 req/min | 30 req/min |
| **API Version Enforced** | `2022-11-28` | `2022-11-28` |
| **Zero-Quota Strategy** | `raw.githubusercontent.com` | `raw.githubusercontent.com` for source CSF/READMEs |
| **Conditional Requests** | `If-None-Match` (ETag) enabled | ETag cache hits consume 0 quota |

## Security & Secret Management Architecture

1. **Strict Secret Redaction:**
   * `GITHUB_TOKEN` is typed as a Pydantic `SecretStr` within `Settings` (`app/core/config.py`).
   * The token is never logged, never returned over API endpoints, never written to disk, and never exported in reports.
   * Telemetry (`ApiUsage` table) only records endpoint paths, HTTP statuses, and rate-limit headers.

2. **Least-Privileged Credential Requirement:**
   * Only **read-only public repository access** is needed.
   * Fine-grained Personal Access Tokens (PATs) require only `Public Repositories (read-only)` permission. No account, user, or organization admin permissions should ever be granted.

3. **Quota Gating & Abuse Prevention:**
   * The client implements automated pre-call quota gating (`_gate()`): when remaining requests reach 0, calls wait if reset is within 90 seconds, or refuse execution cleanly rather than triggering HTTP 403 secondary abuse detection.
   * Exponential backoff and Retry-After header compliance are strictly enforced.

## Zero-Quota & Caching Optimizations

Before expanding repository targets, the platform reduces avoidable REST calls through three architectural layers:

* **Raw Content Offload:** Storybook CSF source code parsing (e.g., `.stories.tsx`, `.stories.jsx`) and repository READMEs are fetched via `raw.githubusercontent.com`. This consumes **0 REST API requests**, allowing thousands of variant extractions without touching the rate limit.
* **Disk Caching:** All metadata responses are cached on disk (`storage/engine/data/cache/http/`) with ETags and Last-Modified headers, converting repeated checks into HTTP 304 Not Modified.
* **Single-Call Metadata:** Repo verification (`meta()`) extracts license, default branch, stars, and push activity in one single API request.

## Operational Next Steps for Operators

To raise the GitHub API limit from 60 to 5,000 requests/hour:
1. Generate a fine-grained Personal Access Token on GitHub with `Public repositories (read-only)` permissions.
2. Add the token to the backend environment or local git-ignored `backend/.env` file:
   ```bash
   GITHUB_TOKEN=github_pat_your_token_here
   ```
3. Restart the backend or run:
   ```bash
   curl http://localhost:8000/api/v1/admin/integrations/github
   ```
4. Verify that `token_configured: true` and `mode: authenticated` are returned with a limit of 5,000.
