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
.venv/bin/python scripts/manage.py bootstrap-admin   # one-shot first admin from ADMIN_EMAIL / ADMIN_PASSWORD (refuses once an admin exists)

# 2. Run the API and a worker (two terminals)
.venv/bin/uvicorn app.main:app --port 8000 --reload --reload-dir app
.venv/bin/python -m app.workers.main              # add --once to drain the queue and exit

# 3. Frontend (repo root)
npm install
npm run dev                                       # .env.development sets BACKEND_URL=http://127.0.0.1:8000
```

Then sign in at `http://localhost:3000/admin/login`, open **Sources → Crawl all**. Optional: reuse a previous engine cache to avoid re-fetching: `python scripts/manage.py import-cache ../research/data/cache/http`.

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

## Deploying: Vercel (frontend + backend) and Supabase (database + files)

```
           Browser ──https──▶ Vercel project (one domain)
                               ├─ /api/*  → service `backend`  (FastAPI, Python function)  ─┐
                               └─ /*      → service `app`      (Next.js dashboard)          │
                               daemon `worker` (container, no ingress) ─────────────────────┤
                                                                                            ▼
                                            Supabase:  Postgres (via Supavisor pooler)  +  Storage (private bucket)
```

| Name | Kind | Root | Public path | Talks to |
|---|---|---|---|---|
| `app` | Vercel service (Next.js) | `.` | `/(.*)` | nothing server-side; the browser calls `/api/v1` on the same domain |
| `backend` | Vercel service (FastAPI, `app.main:app`) | `backend` | `/api/(.*)` (receives `/api/v1/...` unchanged) | Supabase Postgres + Storage |
| `worker` | Vercel daemon (`backend/Dockerfile.worker`) | `backend/` | — | Supabase Postgres + Storage; crawls approved public sites |

No service bindings are declared, because no Vercel service calls another over HTTP. The database is the shared state, and Supabase is an external endpoint configured through environment variables.

### 1. Supabase

1. Create a project. Pick its region and note it, so the Vercel functions and the worker can run near it.
2. **Database → Connect:** copy the *Transaction pooler* URI (port 6543) and the *Session pooler* URI (port 5432). Rewrite each as `postgresql+psycopg://…?sslmode=require`. Vercel egress is IPv4, so use the pooler hostnames rather than the direct `db.<ref>.supabase.co` address.
3. **Project Settings → API keys:** copy the project URL and the **service-role / secret** key. It is server-side only.
4. From a trusted machine, run the migrations, the one-shot admin bootstrap and the private bucket setup:

```bash
cd backend
export DATABASE_URL='postgresql+psycopg://postgres.<ref>:<pw>@aws-0-<region>.pooler.supabase.com:6543/postgres?sslmode=require'
export MIGRATION_DATABASE_URL='postgresql+psycopg://postgres.<ref>:<pw>@aws-0-<region>.pooler.supabase.com:5432/postgres?sslmode=require'
.venv/bin/alembic upgrade head                      # also locks the Data API out of every table (see below)
ADMIN_EMAIL=… ADMIN_PASSWORD=… .venv/bin/python scripts/manage.py bootstrap-admin
STORAGE_BACKEND=supabase SUPABASE_URL=https://<ref>.supabase.co SUPABASE_SERVICE_ROLE_KEY=… .venv/bin/python scripts/manage.py setup-storage
.venv/bin/python scripts/manage.py seed             # register the seed sources
```

**Supabase Data API lockdown.** Supabase auto-exposes the `public` schema to its `anon` and `authenticated` roles through PostgREST. This application never uses that API; all access goes through the FastAPI backend and its administrator session. After every `alembic upgrade`, `app/database/supabase.py`:
* revokes all table, sequence and function privileges, including default privileges, from those roles;
* enables row-level security with no policies on every table.

The app connects as the table owner, which RLS does not restrict. Re-apply it any time with `manage.py supabase-lockdown`. Optionally also disable the Data API under Project Settings → API.

**Moving the existing knowledge base (one command).** `backend/scripts/supabase_setup.py` restores a `pg_dump` of the local database into the empty project, then:
* runs the migrations and the Data API lockdown;
* creates the private bucket;
* uploads the local raw snapshots and exports;
* verifies row counts, privileges and RLS.

Credentials come from your shell, and only hostnames are printed:

```bash
cd backend
export MIGRATION_DATABASE_URL='postgresql+psycopg://postgres.<ref>:<pw>@aws-0-<region>.pooler.supabase.com:5432/postgres?sslmode=require'
export SUPABASE_URL='https://<ref>.supabase.co' SUPABASE_SERVICE_ROLE_KEY='…'
.venv/bin/python scripts/supabase_setup.py all --dump ../backups/dsrp-20261022T071629Z-for-supabase.dump
```

Each step (`check`, `data`, `schema`, `bucket`, `objects`, `verify`) can be run on its own, and each is idempotent: `data` refuses a non-empty database. The administrator accounts come across with the data, so `bootstrap-admin` is only needed for a fresh, empty start.

### 2. Vercel

Import the repository; `vercel.json` defines the services, routing and daemon. Project environment variables (Production; add Preview if previews should use a separate Supabase project):

| Variable | Value |
|---|---|
| `DATABASE_URL` | transaction pooler URI (port 6543). Detected automatically: no client pool, no prepared statements, no session `SET`s. |
| `SECRET_KEY` | ≥ 32 random characters |
| `ENVIRONMENT` | `production` (disables the interactive API docs) |
| `COOKIE_SECURE` | `true` |
| `STORAGE_BACKEND` | `supabase` |
| `SUPABASE_URL` | `https://<ref>.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | the secret key, marked **Sensitive**. Never prefix it with `NEXT_PUBLIC_`. |
| `SUPABASE_STORAGE_BUCKET` | `dsrp-private` (default) |
| `GITHUB_TOKEN` | optional |

Do **not** set `BACKEND_URL` on Vercel. That `next.config.ts` rewrite is for local `next dev` only; the top-level rewrite already routes `/api/*` to `backend`.

Set the Functions region (Project Settings → Functions) and the worker's `instances` region in `vercel.json` to match the Supabase region.

### Files and downloads

Raw page snapshots and exports go to the private bucket. Download endpoints first authorize the administrator, then redirect (303) to a 60-second signed Supabase URL that forces an attachment. Large exports therefore never pass through the function response-size limit, and stored HTML is never rendered on the app's origin.

### Constraints

* **Previews.** During Vercel's beta, daemons run in production only, so jobs queued from preview deployments wait until a production worker runs. Use a separate Supabase project for previews if they must not touch production data.
* **Local development.** `vercel dev` runs `app` and `backend` but not daemons. Run `python -m app.workers.main` alongside it, or `docker build -f backend/Dockerfile.worker backend/`.
* **Rate limits.** Login and intake limits are per instance.
* **Engine cache.** The crawler's HTTP cache lives in the worker's ephemeral `/tmp` and is rebuilt after restarts.


## Daily synchronization — operation, monitoring and recovery

**Where it runs.** Every worker process (the Vercel daemon `worker` in production; `python -m app.workers.main` locally) runs a scheduler tick every `SCHEDULER_TICK_SECONDS` (30 s).
* The tick claims the run only when `sync_schedule.next_run_at` has passed, using `SELECT … FOR UPDATE SKIP LOCKED`. It advances `next_run_at` in the same transaction.
* A partial unique index allows only one `running` run.
* So scaling the worker, restarting it, or the hourly Vercel Cron backup (`/api/v1/internal/cron/sync`, needs `CRON_SECRET`) can never start two runs.
* The schedule lives in the database, so it survives restarts and redeploys. Times are stored and run in **UTC**; the admin page also shows your local time.

**What a run does.**
1. Snapshot counts.
2. Queue a `refresh` crawl of every enabled (not paused) source; sources already being crawled are skipped and reported.
3. Ingest compares each record's fingerprint. New records are inserted; changed ones are updated, with `content_updated_at` set and a `record_changes` row written. Unchanged records get **no write**.
4. Records missing from a crawl are marked stale only after a complete, error-free crawl, and only if at most 30 % of the source's records went missing. Otherwise they are kept and reported as "kept for review".
5. `sync_finalize` retries failed sources once after 10 minutes.
6. The canonical dataset is rebuilt **only if some source changed**. The rebuild itself writes only rows whose fingerprint differs.
7. Metrics, per-source outcomes and errors are stored in `sync_runs`.

**Monitoring.** Admin → **Daily sync** shows:
* whether the scheduler is enabled;
* the worker heartbeat (red if none in 10 minutes);
* next run, current run, last run and last successful run;
* history with per-source outcomes and the content-change log.

The admin dashboard shows the same summary.

**Run outcomes.**
* `succeeded`: every source checked.
* `partially_succeeded`: some sources failed or were incomplete (rate limits, timeouts); their existing data is preserved.
* `failed`: every source failed.
* `interrupted`: the run had no active jobs for 8 hours, e.g. the worker was down. It is marked automatically, and the next scheduled run proceeds normally.

**Recovery.**
* *Worker was down at run time*: the next tick after it comes back claims the overdue run immediately.
* *A source keeps failing*: check Admin → Sources → the source (its `last_change_summary`, `consecutive_failures`, and job events), then pause it or fix its URL. Its data stays published meanwhile.
* *Run now*: Admin → Daily sync → **Run now**. It is refused while another run is in progress.
* *Disable automatic runs*: switch the toggle off in Admin → Daily sync. Manual runs still work.

**Verified no-change behaviour.**
* Automated: `tests/test_daily_sync.py` covers cases A–G and the scheduler.
* On the real dataset, a second full build reported all 430 systems, 3,397 components, 1,708 tokens and 1,997 guidelines unchanged, with zero writes.
* Two consecutive live syncs of designsystems.one and Garden's docs:
  * The first added the 2 genuinely new systems (Magma, workload.zero).
  * The second reported 0 changed, 906 unchanged, no rebuild and no change rows.
