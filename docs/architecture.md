# Architecture & data flows

The Design Systems Research Platform is a **modular monolith** with **separate worker processes**:

```
Browser ──HTTPS──▶ Next.js frontend (repo root)            ──same-origin /api/v1 proxy──▶ FastAPI backend (backend/)
                   • UI, routing, client state                                          • admin auth, validation, business logic
                   • typed API client + bounded query cache                             • search, comparisons, reports, exports
                   • no data, no secrets, no scraping                                   • source registry & job orchestration
                                                                                              │
                                     ┌────────────────────────────────────────────────────────┼──────────────────────┐
                                     ▼                                                        ▼                      ▼
                               PostgreSQL (canonical store)                     Worker processes (python -m      Object storage
                               records, projections, jobs,                      app.workers.main): crawl, build,  (local FS adapter):
                               evidence, audit, FTS indexes                     export — durable queue in jobs    raw snapshots, exports,
                                                                                table (FOR UPDATE SKIP LOCKED)     engine HTTP cache
                                                                                     │
                                                                                     ▼
                                                                    Scraping engine (backend/app/scrapers/dskb):
                                                                    polite fetcher (robots, rate limits, SSRF guard,
                                                                    safe redirects, cache) + 19 source adapters
                                                                                     │
                                                                                     ▼
                                                                         Approved public sources (20 seeds + user)
```

## What belongs where

| Concern | Frontend (Next.js) | Backend (FastAPI + workers) |
|---|---|---|
| Rendering, navigation, URL filter state | ✅ | — |
| Temporary UI state, bounded query cache (30 s stale / 5 min GC) | ✅ | — |
| Input pre-validation (UX) | ✅ | ✅ authoritative |
| Authentication, sessions, CSRF, administrator-only access | hint only (`isAdmin()`) | ✅ enforced on every route |
| Source registry, crawl config, approved domains | — | ✅ |
| Crawling, extraction, normalization, dedupe, categorization | — | ✅ workers |
| Search, filtering, pagination, aggregation | sends parameters | ✅ PostgreSQL |
| Comparisons, reports, exports | displays / requests | ✅ generated |
| Secrets (DB URL, signing key) | never | ✅ environment only |

The frontend never imports research data: platform pages hold no datasets, and a bundle scan (`.next/static`) for DB-only strings, credentials and DSNs returned zero matches. The former public editorial site and its bundled dataset were removed; the application is a private dashboard only.

## Where data is stored

| Data | Store |
|---|---|
| Users, roles, settings (no secrets), audit trail | PostgreSQL `users`, `app_settings`, `audit_events` |
| Source registry + latest coverage | `sources` |
| Jobs (crawl/build/export) + event log | `jobs`, `job_events` |
| Every URL requested and its outcome | `discovered_urls` |
| Raw page snapshots | bytes in object storage (`storage/objects/raw/<sha>`), metadata in `raw_documents` (content-addressed, deduplicated) |
| Extracted findings (all types) | `records` (deterministic `record_key`, JSONB `content`, weighted `tsvector`) |
| Provenance | `evidence` (record → URL, section, version, raw snapshot) |
| Canonical systems | `design_systems` (stable ids, conflicts, aliases, source keys) |
| Query projections | `components`, `component_props`, `design_tokens`, `token_references`, `guidelines` |
| Relationships / review queue | `entity_relationships`, `duplicate_groups` |
| Comparisons, generated reports | `comparisons`, `reports` |
| Export files | object storage `exports/<job_id>/…`, metadata in `jobs.result` |

## Endpoints per frontend section

| Section (route) | Endpoints |
|---|---|
| Dashboard `/platform` | `GET /dashboard/summary`, `/dashboard/activity`, `/dashboard/source-coverage`, `/dashboard/category-distribution` |
| Sources `/platform/sources[/id]` | `GET/POST /sources`, `GET/PATCH /sources/{id}`, `GET /sources/{id}/coverage`, `/documents`, `/jobs`, `POST /sources/{id}/crawl`, `GET /documents/{id}[/content]` |
| Crawl jobs `/platform/jobs[/id]` | `GET/POST /crawl-jobs`, `POST /crawl-jobs/build`, `GET /crawl-jobs/{id}`, `/events`, `POST /cancel`, `/retry` |
| Design systems `/platform/systems[/id]` | `GET /design-systems`, `/facets`, `GET/PATCH /design-systems/{id}`, `/components`, `/tokens`, `/guidelines`, `/sources` |
| Components `/platform/components[/id]` | `GET /components`, `/facets`, `/components/{id}`, `/evidence`, `/related-tokens`, `/related-guidelines`, `/related-components` |
| Tokens `/platform/tokens` | `GET /tokens`, `/facets`, `/tokens/{id}`, `/references`, `/dependents` |
| Guidelines & patterns | `GET /guidelines`, `/guidelines/facets`, `/guidelines/{id}`, `GET /patterns`, `/patterns/{id}`, `GET /records/{id}` |
| Search `/platform/search` + top bar | `GET /search` |
| Compare `/platform/compare[/id]` | `GET/POST /comparisons`, `GET/PATCH/DELETE /comparisons/{id}`, `POST /comparisons/{id}/generate`, `GET /comparisons/dimensions` |
| Reports & exports `/platform/reports` | `GET /reports`, `/reports/{id}`, `GET/POST /export-jobs`, `GET /export-jobs/{id}`, `POST /download-link`, `GET /download` |
| Review queue `/platform/review` | `GET /review-queue`, `PATCH /review-queue/{id}` |
| Administration `/platform/admin` | `POST /auth/password`, `GET /admin/audit-events`, `GET/PATCH /admin/configuration`, `GET /admin/job-health` |
| Add source `/platform/add` | `POST /intake/check`, `POST /intake` |
| Data quality `/platform/quality` | `GET /quality`, `GET /quality/issues`, `POST /resources/verify` |
| System resources | `GET/POST /design-systems/{id}/resources`, `GET /resources`, `PATCH/DELETE /resources/{id}` |
| Review decisions | `POST /review-queue/{id}/decide` (merge / keep separate) |
| Auth | `POST /auth/login`, `POST /auth/logout`, `GET /auth/me` |

Full contract: `backend/openapi.json` (served at `/api/v1/openapi.json`, docs at `/api/v1/docs`). 67 paths / 77 operations.

## How a crawl updates persistent records

1. `POST /sources/{id}/crawl` (administrator, CSRF-checked) → `jobs` row `queued` (+ a dependent `build` job). Duplicate active crawls for a source are rejected (409). Response `202 {job_ids}`.
2. A worker claims it (`UPDATE … WHERE id = (SELECT … FOR UPDATE SKIP LOCKED)`), applies admin settings (approved domains, delays, timeouts) to the engine fetcher, and registers a **fetch listener** for the source.
3. The source adapter runs. Every fetch passes: scheme check → domain allow-list → deny patterns → **public-IP SSRF check** → robots.txt → per-host delay → manual redirect following with per-hop re-validation → size cap. Each outcome is written to `discovered_urls`; successful bodies are stored content-addressed in object storage (`raw_documents`).
4. The listener heartbeats progress every ~2 s (`urls_discovered/processed`, `error_count`, phase) and raises `JobCancelled` if cancellation was requested.
5. **Ingest** (one transaction): engine normalization/categorization → upsert by `record_key` (idempotent) → evidence rows linked to raw snapshots → records of this source not re-observed are marked `is_stale` (never deleted) → source status/coverage updated from the adapter's own outcome.
6. Job finishes `succeeded` / `partially_succeeded` / `failed` / `cancelled`. Crawl failures are not blindly auto-retried (retry is a user action); build/export jobs retry with exponential backoff. Jobs with expired heartbeats are re-queued on worker start.
7. The **build** job waits for its upstream crawls (re-queues itself without consuming attempts), then, under an advisory lock and in one transaction: cross-source entity resolution → upsert `design_systems` by key (stable ids) → rebuild projections (components/props, tokens/references, guidelines, relationships) → refresh the review queue (human decisions preserved) → generate reports.
8. The frontend's job page polls `GET /crawl-jobs/{id}` (2 s while active); when the job reaches a terminal state it invalidates dashboard/source/catalog queries.

## Search, comparison and export

* **Search** — `records.search_vector` is a generated, weighted `tsvector` (title A, system/org B, summary C) with a GIN index; systems and sources have their own. `GET /search` builds a prefix `tsquery` from sanitized terms, unions record/system/source hits, ranks with `ts_rank_cd`, returns `ts_headline` snippets and per-type facet counts. If no record contains all terms it falls back to any-term matching and reports `meta.facets._match_mode = "any"`. Catalog endpoints combine FTS with `ILIKE` on names (trigram-indexed when `pg_trgm` is installed).
* **Comparison** — `POST /comparisons` stores the configuration and generates synchronously (≤ 6 items, bounded queries). Each cell is `documented` (value + evidence URLs), `not_documented`, or `not_applicable` (e.g. styling tokens for headless libraries). Analytical observations are returned separately as `interpretation`.
* **Export** — `POST /export-jobs` → worker writes the file to `exports/<job_id>/` and records size/rows/expiry. Downloads require an administrator session (or a 10-minute signed link from `POST /download-link`), set `Content-Disposition: attachment`, `no-store`, and expire after `EXPORT_TTL_HOURS`.

## Extending safely

* **New source type** — add an adapter in `backend/app/scrapers/dskb/adapters/` returning `{records, coverage}` in the engine record shape, register it in `app/workers/crawl.py: ADAPTERS`, and add the domain to approved domains. Use `FETCHER.get(…, source_id=key)` so politeness, SSRF checks, provenance and progress apply automatically.
* **New record field** — put source-specific detail in `content` (JSONB); promote to a projection column + migration only when it is filtered/sorted on.
* **New endpoint** — route (HTTP only) → service (rules) → repository (queries); add a schema; regenerate `openapi.json` and `npm run api:types`; CI fails if either drifts.
* **Scale out** — API instances are stateless; run more workers (queue uses `SKIP LOCKED`); swap `LocalStorage` for an S3 implementation of the same interface; introduce Redis/a search engine only when measured load requires it.


## Canonical systems, deduplication and resources

**One canonical record per distinct system.** Every build runs the following steps:

1. The engine groups source records by documentation site key and repository key.
2. `services/identity.apply` merges records from sources registered for a system (`sources.system_key`: official docs crawls and admin intake) into that system.
3. It applies persisted `identity_links` (`same_as`, `implementation_of`, `related_to`, `distinct_from`) decided by the evidence resolver or an administrator.
4. It re-applies `entity_curation` (resolver-verified values and audited admin edits), so edits survive rebuilds.
5. Same-name entities that no decision covers become `possible_duplicate_system` review items for the resolver (`services/review_resolver`). The resolver uses redirect, cross-link, shared repository/Storybook and organization evidence; a name match alone never merges.
6. A system key that disappears in a merge is written to `system_aliases` (old key, old id, canonical key, reason) before its row is removed. `GET /design-systems/{old_id}` returns the canonical system with `requested_alias`.
7. Related rows follow the canonical system: components, tokens and guidelines through their records, `attribute_evidence` through `system_key` and aliases, Storybook projects through their showcase record, and links through `system_resources.system_key`.

**Typed links (`system_resources`).** Each link has a type: `official_website`, `official_documentation`, `github_repository`, `figma_file`, `storybook` or `additional_resource`. It also records its URL and canonical URL, origin (directory, official docs crawl, official page, Storybook showcase, manual), the source keys that listed it, verification status (`verified` / `unverified` / `invalid`), method, evidence URL/note, HTTP status, access note and last-checked time.

`services/resources.sync` re-derives links on every build. It keeps provenance and never downgrades a decision made by the verifier or the administrator.

`services/resources.verify` (job kind `verify_resources`) fetches each system's primary official page through the polite fetcher:
* It marks the page invalid on 404/410/5xx.
* It confirms repository, Figma and Storybook links that the page publishes, discovering new ones where present.
* A repository counts as verified only with ownership evidence (owner or name matches the system, organization or site, or an owner already associated with the system).
* Figma design files are recognised by URL shape and canonicalised without view parameters. Profile pages, plugins and the community landing page are not design files.
* URLs are never constructed.

**Intake.** `POST /intake/check` returns likely existing systems: same URL, same docs site, same host, same repository owner, same name. `POST /intake` attaches the URL to one of them, or creates a separate system. Creating one requires `separate_from` (recorded as `distinct_from` links) and is refused outright when the docs site already belongs to a system. Official URLs are registered as a bound source, then crawl → build → verify jobs are queued.
