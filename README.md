# Design Systems Directory

A public directory of design systems — components, variants, design tokens, guidelines, Storybook stories and official resource links —
with a private administration area and an automated daily synchronization that keeps the data current.

| Part | Path | Who | Owns |
|---|---|---|---|
| **Public directory** | `src/app/(public)` → `/` (landing), `/systems`, per-system workspaces `/systems/{system}` (`/foundations`, `/components/{component}[/playground]`, `/tokens/{token}`, `/patterns/{pattern}`, `/playground`, `/resources`), global `/components`, `/tokens`, `/patterns`, `/playground`, `/compare`, `/search`, `/about`, `/attribution`, `/privacy` | anyone, no account | Server-rendered discovery organised by design system; interactive playgrounds that render each system's own package; no internal status labels |
| **Administration** | `src/app/admin` → `/admin`, `/admin/sync`, `/admin/systems`, `/admin/add`, `/admin/sources`, `/admin/jobs`, `/admin/quality`, `/admin/review`, `/admin/reports`, `/admin/settings` | the administrator | sources, crawls, data quality, duplicate review, record editing, sync schedule |
| **Backend API** | `backend/app` (`/api/v1`) | — | public read-only endpoints (`public:read`) and admin endpoints (session-enforced on every request) |
| **Worker** | `backend/app/workers` | — | crawls, rebuilds, verification, and the **daily synchronization** scheduler |
| **Database** | PostgreSQL (Supabase in production) | — | the single source of truth, content fingerprints, change history, sync runs |

**Daily synchronization.** Every 24 hours (default 03:00 UTC, set in Admin → Daily sync) the worker re-checks every enabled source:
* It uses conditional requests (ETag / Last-Modified) and compares content fingerprints per record.
* New information is added and changed records are updated.
* **Unchanged content is not written at all:** no new versions and no `content_updated_at` change; only "last checked" moves.
* A failing or rate-limited source is retried once and never hides existing data.
* Every run is recorded with real metrics and a per-record change log.

**Frontend stack (public directory).** Next.js App Router with Server Components, Tailwind CSS v4 on the shared design
tokens, Radix primitives in shadcn-style components, Motion for React for interface motion, GSAP for the two narrative
scroll story on the landing page, and a minimal hero with a design-system specimen illustration. Reduced motion
is honoured everywhere. Interactive playgrounds render Mantine, Ant Design, React Aria, Base UI and Radix at their documented
versions in an isolated frame, plus a labelled shadcn/ui adapter. See [`docs/design-system.md`](docs/design-system.md) and the
*System hierarchy* section of [`docs/architecture.md`](docs/architecture.md).

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
BACKEND_URL=http://localhost:8000 npm run dev        # http://localhost:3000 (directory) · /admin (administration)
```

`BACKEND_URL` is read on the server only; the browser talks to the same origin, and `/api/v1/*` is proxied. For `npm run build`, set `BACKEND_URL` at **build time**, because Next.js bakes rewrites into the build. The public directory is at http://localhost:3000; the administration area is at http://localhost:3000/admin.

## Administrator access (administration area only — the directory needs no account)

* **First administrator:** `manage.py bootstrap-admin` from a shell on the server. It reads `ADMIN_EMAIL`/`ADMIN_PASSWORD` from the environment or `backend/.env`, and refuses to run once any administrator exists. There is no HTTP endpoint that can create an account.
* **Change password:** Settings → Account. This signs out every other session.
* **Forgotten password:** `manage.py reset-admin-password <email>` from a shell on the server. The password comes from `ADMIN_PASSWORD` or a hidden prompt, and every session is signed out.
* Published data (`public:read`) needs no account. Every other API route requires an active administrator session (httpOnly cookie plus CSRF header, or a Bearer token): sources, crawls, jobs, raw documents, review, quality, exports, settings and sync. API responses carry `X-Robots-Tag: noindex`, and the interactive API docs are disabled in production.

## Commands

| Task | Command |
|---|---|
| Backend tests | `cd backend && .venv/bin/python -m pytest -q` |
| Dashboard tests / types / build | `npm test` · `npm run typecheck` · `BACKEND_URL=… npm run build` |
| Regenerate API contract | `cd backend && .venv/bin/python scripts/manage.py openapi openapi.json && cd .. && npm run api:types` |
| Refresh slugs, token groups, family taxonomy | `cd backend && .venv/bin/python scripts/manage.py refresh-catalog` (also runs after every build) |
| Collect official logos / share images | `cd backend && .venv/bin/python scripts/manage.py collect-assets [ids]` or Admin → system → Visual assets |
| Rebuild the canonical dataset | Crawl jobs → *Rebuild knowledge base* (or queue a `build` job) |
| Re-check official pages (links, Figma, GitHub) | Data quality → *Re-check all official pages* |
| Regenerate KB reports | `cd backend && .venv/bin/python scripts/export_kb_reports.py` |
| New migration | `cd backend && .venv/bin/alembic revision --autogenerate -m "…"` (test on a scratch copy first) |

## Documentation

* [`docs/architecture.md`](docs/architecture.md) — boundaries, data model, crawl → canonical record flow, deduplication, resources
* [`docs/design-system.md`](docs/design-system.md) — public experience: tokens, components, rendering, motion conventions, accessibility
* [`docs/operations.md`](docs/operations.md) — configuration, deployment, backup/restore, observability
* [`docs/known-issues.md`](docs/known-issues.md) — limitations
* [`research/output/deduplication_report.md`](research/output/deduplication_report.md), [`data_reconciliation_report.md`](research/output/data_reconciliation_report.md), [`canonical_identity_map.json`](research/output/canonical_identity_map.json) — generated from the database
