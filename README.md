# Design Systems Research Platform (+ DS Atlas)

A full-stack platform that collects, stores, searches, compares and reports on design-system knowledge from 20 seed sources (directories, component libraries, token specifications, GitHub repositories, resource guides) — plus the original editorial **DS Atlas** site.

| Part | Path | Stack | Owns |
|---|---|---|---|
| **Frontend** | repo root (`src/`) | Next.js 16, TypeScript, SCSS modules, TanStack Query, Framer Motion/GSAP | UI, routing, client state; talks only to `/api/v1` |
| **Backend API** | `backend/app` | FastAPI, Pydantic, SQLAlchemy 2, Alembic | auth/RBAC, validation, business logic, search, comparisons, reports, exports |
| **Workers** | `backend/app/workers` | same codebase, separate process | crawl / build / export jobs from a durable PostgreSQL queue |
| **Scraping engine** | `backend/app/scrapers/dskb` | requests, BeautifulSoup, GitHub API | polite, robots-aware, SSRF-guarded fetching + 19 source adapters |
| **Database** | PostgreSQL | — | canonical store for every record, job, evidence row and setting |

Routes: editorial Atlas at `/`, `/systems`, `/directories`, `/resources`, `/foundations`, `/checklist`; the research platform at **`/platform`** (dashboard, sources & crawl jobs, design systems, components, tokens, guidelines & patterns, search, comparisons, reports & exports, review queue, administration). API docs at `/api/v1/docs`.

## Quick start (local)

```bash
# backend
cd backend
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r requirements-dev.txt
.venv/bin/python scripts/devdb.py start            # embedded dev PostgreSQL (or point DATABASE_URL at your own)
cp .env.example .env                                # fill DATABASE_URL, SECRET_KEY, ADMIN_EMAIL, ADMIN_PASSWORD
.venv/bin/alembic upgrade head
.venv/bin/python scripts/manage.py seed && .venv/bin/python scripts/manage.py create-admin
.venv/bin/uvicorn app.main:app --port 8000           # terminal 1
.venv/bin/python -m app.workers.main                 # terminal 2

# frontend (repo root)
npm install && npm run dev                           # http://localhost:3000/platform
```

Sign in, open **Sources → Crawl all**, and watch the jobs populate the knowledge base.

## Commands

| Task | Command |
|---|---|
| Backend tests | `cd backend && .venv/bin/python -m pytest -q` |
| Frontend tests / types / build | `npm test` · `npm run typecheck` · `npm run build` |
| Regenerate API contract | `cd backend && .venv/bin/python scripts/manage.py openapi openapi.json && cd .. && npm run api:types` |
| New migration | `cd backend && .venv/bin/alembic revision --autogenerate -m "…"` |
| Drain the job queue once | `cd backend && .venv/bin/python -m app.workers.main --once` |
| File-based research exports (CLI) | `cd research && ../backend/.venv/bin/python run.py build` |

## Documentation

* [`docs/architecture.md`](docs/architecture.md) — boundaries, storage, endpoint map per page, crawl → record flow, search/comparison/export, extension guide
* [`docs/adr/0001-platform-architecture.md`](docs/adr/0001-platform-architecture.md) — key decisions
* [`docs/operations.md`](docs/operations.md) — configuration, deployment, backup/restore, observability, performance baseline
* [`docs/gap-analysis-and-status.md`](docs/gap-analysis-and-status.md) — starting point, acceptance status, test results
* [`docs/known-issues.md`](docs/known-issues.md) — incomplete features and limitations
* [`research/output/`](research/output) — the earlier file-based research deliverables (reports, JSONL, SQLite, XLSX)
