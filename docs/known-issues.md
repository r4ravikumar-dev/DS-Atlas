# Known issues, incomplete features & limitations

## Not implemented / partial
* **Scheduled crawls** — schedule settings are stored and editable but no scheduler executes them; crawls are triggered via UI/API.
* **Retention purging** — retention settings exist; no job yet deletes old raw documents/job events/exports (expired exports are refused at download time).
* **Server-sent events** — job progress uses polling (2 s while active), not SSE.
* **`POST /design-systems`** (manual system creation) is intentionally not implemented: canonical systems are derived from source records. Curators can `PATCH` descriptive fields.
* **Large comparisons as background jobs** — comparisons are synchronous and capped at 6 items.
* **Password reset / SSO** — admins create users and initial passwords; no self-service reset or OIDC yet.
* **Login rate limiting** is per-process memory (fine for one API instance; use a shared store behind a load balancer).
* **Accessibility** — designed for keyboard and screen readers (semantic tables, labelled inputs, focus management in dialogs) but no automated axe/Lighthouse audit has been run.
* **Container files** (`Dockerfile*`, `docker-compose.yml`) and the **CI workflow** were authored but not executed in this environment (no Docker / no CI runner).

## Data limitations (inherited from sources)
* S05 Design Systems Directory is a Google Programmable Search front-end — its catalogue cannot be enumerated; only metadata is stored.
* S19's supplied repository returns 404; items come from the substitute `ardakaracizmeli/design-system-checklist` linked by designsystemchecklist.com (recorded as such).
* ~2,600 component records are directory-level links (`detail_level: index`); the linked official pages were not crawled.
* Directory attributes are third-party claims; only S11–S16 libraries are verified against official docs.
* Storybook instances listed by the showcase were not crawled (catalog + metadata only).
* React Aria documents keyboard behaviour mostly in prose, so its keyboard table count is 0; API tables include inherited DOM/ARIA props.
* The embedded dev PostgreSQL lacks `pg_trgm`; trigram indexes are created automatically on servers that have it.

## Operational notes
* Workers do not hot-reload; restart them after deploying engine changes.
* The engine fetcher is process-global; per-job settings are applied under a lock before each crawl. Run separate worker processes if different crawl policies must run concurrently.
* The root `README` also lists the editorial Atlas pages, whose content is hand-curated and independent of the platform database.
