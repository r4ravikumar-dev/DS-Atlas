# ADR 0001 — Platform architecture

* Status: accepted · Date: 2026-10-21

## Context
The repository contained (a) a Next.js 16 + SCSS editorial site ("DS Atlas") backed by hand-curated arrays and (b) a file-based Python research engine (`research/dskb`) that crawled the 20 seed sources. The new requirement is a production-oriented platform where the backend owns all research data and the frontend consumes it only through a versioned API. The development machine has no Docker, PostgreSQL, Redis or Homebrew and only Python 3.9.

## Decisions
1. **Keep the existing Next.js app as the frontend**, add the platform under `/platform` with its own shell (route group `(atlas)` keeps the editorial site intact). Reuse its SCSS tokens, fonts, theming and motion libraries.
2. **Backend: FastAPI + SQLAlchemy 2 + Alembic on Python 3.12** (installed via `uv`), layered as routes → services → repositories, with Pydantic schemas decoupled from tables.
3. **PostgreSQL is canonical.** JSONB for source-specific content; relational projections for everything filtered/sorted. Local development uses an embedded PostgreSQL (`pgserver`, `scripts/devdb.py`); any PostgreSQL works via `DATABASE_URL`.
4. **Durable queue in PostgreSQL** (`jobs` + `FOR UPDATE SKIP LOCKED`, heartbeats, recovery) instead of Redis — fewer moving parts until throughput demands otherwise.
5. **Reuse the research engine** by moving it into `backend/app/scrapers/dskb` (single copy; the research CLI now imports it). Add fetch listeners, SSRF protection and per-hop redirect validation rather than rewriting adapters.
6. **Auth:** Argon2id password hashes (pwdlib) + signed expiring session tokens (JWT HS256) in an httpOnly SameSite=Lax cookie, double-submit CSRF for cookie-authenticated mutations, Bearer tokens for API clients. Roles: admin / researcher / viewer, enforced server-side.
7. **Same-origin proxy:** the browser calls `/api/v1/*` on the frontend origin; Next rewrites to `BACKEND_URL` (server-only env). No CORS needed by default; no backend address in client bundles.
8. **Contract-first types:** `backend/openapi.json` is committed; frontend types are generated with `openapi-typescript`; CI fails on drift.
9. **Object storage abstraction** with a local-filesystem implementation (content-addressed raw snapshots, exports).

## Consequences
* One deployable backend image serves both API and workers (different commands).
* Without `pg_trgm` (absent from the embedded build) name search falls back to un-indexed `ILIKE`; the migration creates trigram indexes automatically where the extension exists.
* Scheduling configuration is stored but not executed automatically (no scheduler service yet).
