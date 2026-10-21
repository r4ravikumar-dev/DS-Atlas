# Development, deployment & operations

## Local development (as used to build this repo)

```bash
# 1. Backend environment (Python 3.12 via uv; any 3.11+ works)
cd backend
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r requirements-dev.txt
.venv/bin/python scripts/devdb.py start          # embedded PostgreSQL (dev only) → prints DATABASE_URL
cp .env.example .env                              # set DATABASE_URL, SECRET_KEY, ADMIN_EMAIL, ADMIN_PASSWORD
.venv/bin/alembic upgrade head                    # migrations
.venv/bin/python scripts/manage.py seed           # register the 20 seed sources (idempotent)
.venv/bin/python scripts/manage.py create-admin   # admin from ADMIN_EMAIL / ADMIN_PASSWORD

# 2. Run the API and a worker (two terminals)
.venv/bin/uvicorn app.main:app --port 8000 --reload --reload-dir app
.venv/bin/python -m app.workers.main              # add --once to drain the queue and exit

# 3. Frontend (repo root)
npm install
npm run dev                                       # .env.development sets BACKEND_URL=http://127.0.0.1:8000
```

Then sign in at `http://localhost:3000/platform/login`, open **Sources → Crawl all**. Optional: reuse a previous engine cache to avoid re-fetching: `python scripts/manage.py import-cache ../research/data/cache/http`.

## Tests

```bash
cd backend && .venv/bin/python -m pytest -q      # uses database dsrp_test (or TEST_DATABASE_URL)
npm test                                          # Vitest (repo root)
npm run typecheck && npm run build
npm run api:check                                 # regenerate API types; fails if they drift from backend/openapi.json
```

## Configuration

| Variable | Where | Purpose |
|---|---|---|
| `DATABASE_URL` | backend | PostgreSQL DSN (`postgresql+psycopg://…`) |
| `SECRET_KEY` | backend | ≥ 32 chars; signs sessions & download links |
| `COOKIE_SECURE` | backend | `true` behind HTTPS |
| `ALLOW_ANONYMOUS_READ` | backend | allow unauthenticated read/search |
| `CORS_ORIGINS` | backend | only if the frontend is not served via the same-origin proxy |
| `STORAGE_DIR` | backend | object storage root (raw snapshots, exports, engine cache) |
| `WORKER_CONCURRENCY`, `EXPORT_TTL_HOURS` | backend | worker threads per process; export expiry |
| `BACKEND_URL` | frontend (server-only) | target of the `/api/v1` proxy |

Operational settings (approved domains, crawl defaults, retention, export policy, schedule, data-quality rules) live in the database and are edited by admins in **Settings**; they never contain secrets.

## Deployment

* Images: `backend/Dockerfile` (API: default command; worker: `python -m app.workers.main`) and `Dockerfile.frontend`. `docker-compose.yml` wires Postgres, a one-shot migrate+seed job, API, worker and web. *These container files were authored but could not be executed in the development environment (no Docker available).*
* Run migrations (`alembic upgrade head`) before rolling out new API/worker versions; migrations are reviewable files in `backend/app/database/migrations/versions`. Downgrades are supported (`alembic downgrade -1`); CI applies up → down → up.
* Put the frontend and API behind HTTPS; set `COOKIE_SECURE=true`. Health: `GET /api/v1/health` (liveness), `GET /api/v1/ready` (DB, migration revision, stale-job check).
* Scale API instances horizontally (stateless). Add worker processes for throughput; the queue is safe for concurrent workers.

## Backup & restore

* Database: `pg_dump -Fc "$DATABASE_URL" > dsrp-$(date +%F).dump` · restore: `pg_restore --clean --if-exists -d "$DATABASE_URL" dsrp-….dump`.
* Object storage: snapshot `STORAGE_DIR/objects` (raw snapshots are content-addressed, so incremental copies are safe). Exports are disposable.
* After restoring, run `alembic upgrade head`, then a **Rebuild knowledge base** job to refresh projections.

## Retention

Defaults (Settings → retention): raw documents 90 days, job events 30 days, exports 24 hours, stale records kept. *Automatic purging is not yet scheduled* — see known issues.

## Observability

* Structured JSON logs with `request_id` (also returned as `X-Request-ID`), method, path, status, duration; requests slower than 1.5 s log a warning.
* Job progress and failures are persisted in `jobs` / `job_events` (visible in the UI); `GET /admin/job-health` reports status counts, stale heartbeats and the oldest queued job.

## Measured performance baseline

Single client, warm cache, embedded PostgreSQL on a laptop, 8,117 records (40 sequential requests per endpoint):

| Endpoint | p50 | p95 |
|---|---|---|
| `GET /dashboard/summary` | 10.7 ms | 14.8 ms |
| `GET /design-systems?q=…` | 3.1 ms | 4.0 ms |
| `GET /components?family=…&has_props=true` | 2.2 ms | 2.6 ms |
| `GET /components/{id}` | 1.7 ms | 2.1 ms |
| `GET /tokens?type=color&theme=dark` | 2.7 ms | 3.4 ms |
| `GET /search?q=dialog keyboard` | 10.1 ms | 11.0 ms |
| `GET /guidelines?q=accessibility` | 7.2 ms | 8.2 ms |

Full crawl of all 20 sources through workers (with the reused HTTP cache): ~2.5 minutes for crawls + ~10 s for the build. This is a baseline, **not** a load test; establish targets against production infrastructure with a concurrent load tool before committing to SLOs.
