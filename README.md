# Design Systems Knowledge Base

A private, administrator-only workspace. It collects design-system information from the web, keeps one canonical record per distinct design system, and shows the whole deduplicated dataset in a dashboard. There is no public site, no public registration, and only one role (administrator).

| Part | Path | Stack | Owns |
|---|---|---|---|
| **Dashboard** | repo root (`src/`) | Next.js 16, TypeScript, SCSS modules, TanStack Query | UI only. Every record comes from the authenticated `/api/v1`; no research data is bundled. |
| **Backend API** | `backend/app` | FastAPI, Pydantic, SQLAlchemy 2, Alembic | admin auth, canonical data, search and filters, deduplication, resource links, data quality, intake |
| **Workers** | `backend/app/workers` | same codebase, separate process | crawl, build, review, Storybook and link-verification jobs from a durable PostgreSQL queue |
| **Scraping engine** | `backend/app/scrapers/dskb` | requests, BeautifulSoup | robots-aware, rate-limited, SSRF-guarded fetching on an approved-domain list, plus source adapters |
| **Database** | PostgreSQL | — | the single source of truth: systems, links, components, variants, tokens, guidelines, Storybook, evidence, jobs |

## Dashboard (all under `/platform`, all behind the administrator login)

* **Overview** — live counts: canonical systems, source references, verified/partial systems, components, stories, variants, tokens, guidelines and patterns, links, missing official links, review backlog, extraction errors, crawl activity. Every tile links to its view.
* **Design systems** — the catalog, filtered and paginated server-side. Search by name/organization/description or by component, and filter by technology, platform, has/verified/missing resource type, source and verification status. Each card shows only links that exist (website, docs, GitHub, Figma, Storybook), each marked verified or directory-listed.
* **System detail** — overview, official resources (with provenance, evidence and admin confirm/flag/primary/remove), verification and crawl status, plus tabs for components, variants and API, tokens, patterns and guidelines, Storybook, evidence and source references. Old IDs of merged records open the canonical system.
* **Add source** — paste a URL. Existing canonical systems are checked first; then attach the URL to one, or explicitly create a separate system. Official URLs are crawled, rebuilt and link-verified automatically.
* **Data quality** — duplicate candidates, missing official URLs, invalid links, unverified GitHub links, broken relationships, extraction failures and sources needing a re-crawl. Absent Figma files are reported separately from unchecked ones.
* Components, Storybook and variants, Tokens, Guidelines, Compare, Reports and exports, Review queue, Sources, Crawl jobs, and Settings and account.

## Quick start (local)

```bash
# backend
cd backend
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r requirements-dev.txt
.venv/bin/python scripts/devdb.py start            # embedded dev PostgreSQL (or point DATABASE_URL at your own)
cp .env.example .env                                # DATABASE_URL, SECRET_KEY, ADMIN_EMAIL, ADMIN_PASSWORD (≥12 chars)
.venv/bin/alembic upgrade head
.venv/bin/python scripts/manage.py seed
.venv/bin/python scripts/manage.py bootstrap-admin  # one-shot: refuses once an administrator exists
.venv/bin/uvicorn app.main:app --port 8000           # terminal 1
.venv/bin/python -m app.workers.main                 # terminal 2

# dashboard (repo root)
npm install
BACKEND_URL=http://localhost:8000 npm run dev        # http://localhost:3000 → /platform
```

`BACKEND_URL` is read on the server only; the browser talks to the same origin, and `/api/v1/*` is proxied. For `npm run build`, set `BACKEND_URL` at **build time**, because Next.js bakes rewrites into the build.

## Administrator access

* **First administrator:** `manage.py bootstrap-admin` from a shell on the server. It reads `ADMIN_EMAIL`/`ADMIN_PASSWORD` from the environment or `backend/.env`, and refuses to run once any administrator exists. There is no HTTP endpoint that can create an account.
* **Change password:** Settings → Account. This signs out every other session.
* **Forgotten password:** `manage.py reset-admin-password <email>` from a shell on the server. The password comes from `ADMIN_PASSWORD` or a hidden prompt, and every session is signed out.
* Every API route except `/health`, `/ready`, `/auth/login`, `/auth/logout` and `/auth/me` requires an active administrator session (httpOnly cookie plus CSRF header, or a Bearer token). Responses carry `X-Robots-Tag: noindex`, and the interactive API docs are disabled in production.

## Commands

| Task | Command |
|---|---|
| Backend tests | `cd backend && .venv/bin/python -m pytest -q` |
| Dashboard tests / types / build | `npm test` · `npm run typecheck` · `BACKEND_URL=… npm run build` |
| Regenerate API contract | `cd backend && .venv/bin/python scripts/manage.py openapi openapi.json && cd .. && npm run api:types` |
| Rebuild the canonical dataset | Crawl jobs → *Rebuild knowledge base* (or queue a `build` job) |
| Re-check official pages (links, Figma, GitHub) | Data quality → *Re-check all official pages* |
| Regenerate KB reports | `cd backend && .venv/bin/python scripts/export_kb_reports.py` |
| New migration | `cd backend && .venv/bin/alembic revision --autogenerate -m "…"` (test on a scratch copy first) |

## Documentation

* [`docs/architecture.md`](docs/architecture.md) — boundaries, data model, crawl → canonical record flow, deduplication, resources
* [`docs/operations.md`](docs/operations.md) — configuration, deployment, backup/restore, observability
* [`docs/known-issues.md`](docs/known-issues.md) — limitations
* [`research/output/deduplication_report.md`](research/output/deduplication_report.md), [`data_reconciliation_report.md`](research/output/data_reconciliation_report.md), [`canonical_identity_map.json`](research/output/canonical_identity_map.json) — generated from the database
