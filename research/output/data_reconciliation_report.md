# Data reconciliation report

Generated 2026-10-22T07:13:14+00:00 from the live database and the authenticated API (`scripts/export_kb_reports.py`).

- Canonical design systems: **430** (baseline 477; 47 confirmed duplicates merged)
- Verification: partially_verified 151, unverified 279

## Records retained

| Table | Before | After |
|---|---:|---:|
| records | 8690 | 9062 |
| components | 3385 | 3397 |
| component_props | 22066 | 22066 |
| design_tokens | 1708 | 1708 |
| guidelines | 1997 | 1997 |
| storybook_projects | 103 | 103 |
| storybook_stories | 17600 | 17600 |
| storybook_variants | 12150 | 12150 |
| attribute_evidence | 312 | 375 |
| sources | 32 | 33 |
| raw_documents | 1600 | 1722 |

## Resource links

| Type | Status | Links |
|---|---|---:|
| additional_resource | unverified | 211 |
| figma_file | unverified | 4 |
| figma_file | verified | 17 |
| github_repository | unverified | 198 |
| github_repository | verified | 139 |
| official_documentation | invalid | 15 |
| official_documentation | unverified | 122 |
| official_documentation | verified | 44 |
| official_website | invalid | 9 |
| official_website | unverified | 258 |
| official_website | verified | 11 |
| storybook | unverified | 131 |
| storybook | verified | 5 |

| Type | Systems with a link | …with a verified link |
|---|---:|---:|
| official_website | 252 | 11 |
| official_documentation | 129 | 44 |
| github_repository | 269 | 105 |
| figma_file | 18 | 15 |
| storybook | 117 | 5 |

Figma profile/community/plugin pages kept but reclassified as additional resources (not design files): 37.

## Relationships

| Check | Before | After |
|---|---:|---:|
| Storybook projects without a system | 63 | 0 |
| components unattached despite system link | — | 0 |
| tokens unattached despite system link | — | 0 |
| guidelines unattached despite system link | — | 0 |
| resources without system | — | 0 |
| evidence without system | — | 0 |
| system records without system | — | 0 |
| system agnostic guidelines (not broken) | — | 490 |

Guidelines without a system come from sources that are not about one system (library-agnostic checklists, specifications and editorial guides); they remain searchable in the Guidelines view. Tool records (e.g. 166 Style Dictionary transforms) are tooling, not design systems, and are not counted.

## Storage → API trace

| Record type | Stored | API total | Match |
|---|---:|---:|:-:|
| design systems | 430 | 430 | ✓ |
| components | 3397 | 3397 | ✓ |
| design tokens | 1708 | 1708 | ✓ |
| guidelines (guideline/specification) | 1942 | 1942 | ✓ |
| patterns | 55 | 55 | ✓ |
| storybook projects | 103 | 103 | ✓ |
| storybook stories | 17600 | 17600 | ✓ |
| component variants | 12150 | 12150 | ✓ |
| resource links (attached) | 1164 | 1164 | ✓ |
| sources | 33 | 33 | ✓ |
| attribute evidence | 375 | 375 | ✓ |
| design systems — last page | 5 | 5 | ✓ |
| anonymous access | — | 401 | ✓ |

## Root causes fixed

- designsystems.one gallery-only entries had no URLs (detail pages never read) → separate name-only catalog entries; adapter now reads detail pages
- official-docs crawl following a redirect produced a new site key → duplicate system; sources registered for a system now bind to it
- name-only collisions were never raised for review; now queued and decided by the evidence resolver (never merged on name alone)
- 63 Storybook projects had no system link (set only when a public index existed); relinked through their showcase listing on every build
- merged systems were hard-deleted with no mapping; old keys/ids now resolve through system_aliases
- administrator edits were overwritten by the next rebuild; edits are now stored as curation and re-applied
- links lived in four loose columns without type, provenance or verification; now typed system_resources with evidence

## Remaining data-quality issues

- systems missing official link: 100
- systems without organization: 112
- invalid links: 24
- storybook projects not indexed: 63
- open review items: 5

Completeness is not claimed beyond these checks: unknown facts stay empty, and a link that is not published in a page's static HTML is reported as not found, not as absent.