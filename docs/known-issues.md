# Known issues, incomplete features & limitations

## Not implemented / partial
* **Scheduled crawls** — schedule settings are stored and editable but no scheduler executes them; crawls are triggered via UI/API.
* **Retention purging** — retention settings exist; no job yet deletes old raw documents/job events/exports (expired exports are refused at download time).
* **Server-sent events** — job progress uses polling (2 s while active), not SSE.
* **Manual system creation** goes through *Add source* (`POST /intake`): a new system is created from its official URL after a duplicate check, then crawled. There is no free-form `POST /design-systems`.
* **Large comparisons as background jobs** — comparisons are synchronous and capped at 6 items.
* **Single administrator model** — no registration, roles or invitations. Password change is in Settings → Account; recovery is shell-only (`manage.py reset-admin-password`). No SSO.
* **Login rate limiting** is per-process memory (fine for one API instance; use a shared store behind a load balancer).
* **Accessibility** — designed for keyboard and screen readers (semantic tables, labelled inputs, focus management in dialogs) but no automated axe/Lighthouse audit has been run.
* **Container files** (`Dockerfile*`, `docker-compose.yml`) and the **CI workflow** were authored but not executed in this environment (no Docker / no CI runner).

## Data limitations (inherited from sources)
* S05 Design Systems Directory is a Google Programmable Search front-end — its catalogue cannot be enumerated; only metadata is stored.
* S19's supplied repository returns 404; items come from the substitute `ardakaracizmeli/design-system-checklist` linked by designsystemchecklist.com (recorded as such).
* ~2,600 component records are directory-level links (`detail_level: index`); the linked official pages were not crawled.
* Directory attributes are third-party claims. Field-level verification exists only where an official-docs crawl recorded evidence (`attribute_evidence`).
* **Link verification reads static HTML only.** Repository, Figma and Storybook links that are rendered only by client-side JavaScript are not seen, so "Figma resource not found" means not published in the page's HTML. It is not proof that no file exists.
* A repository linked from an official page is marked verified only when its owner or name matches the system, its organization or its site. Other linked repositories (dependency credits, community lists) are kept as unverified.
* Some official pages block automated requests or time out; they are reported as unreachable (reachability unknown), not as broken.
* Storybook stories are enumerated only where a public `index.json`/`stories.json` exists.
* Name collisions that the evidence cannot settle stay in the review queue for an administrator decision. Name alone never merges records.
* React Aria documents keyboard behaviour mostly in prose, so its keyboard table count is 0; API tables include inherited DOM/ARIA props.
* The embedded dev PostgreSQL lacks `pg_trgm`; trigram indexes are created automatically on servers that have it.

## Operational notes
* Workers do not hot-reload; restart them after deploying engine changes.
* The engine fetcher is process-global; per-job settings are applied under a lock before each crawl. Run separate worker processes if different crawl policies must run concurrently.
* The public editorial site (DS Atlas) and its bundled hand-curated dataset were removed; `/` redirects to the private dashboard.
* Two administrator accounts exist in the development database (created before the single-admin simplification). Deactivating one is an operator decision.
