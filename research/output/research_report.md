# Design-Systems Research Report

_Generated 2026-10-21T09:52:32+00:00 · schema 1.0.0. All figures are computed from `crawl_report.json` and the validated datasets._

## 1. Executive summary

- **20** seed URLs were attempted; **19** were inspected successfully. Unavailable/partial: S19.
- **1421** URLs were requested (**1413** succeeded); a further **4916** URLs were discovered in records but not fetched (mostly official component pages linked from directories).
- **8117** normalized records were produced, resolving to **510** canonical design-system entities (**136** corroborated by ≥2 independent sources).
- **3038** component records (**396** with structured API/prop data), **1708** token records and **1794** pattern/guideline records.
- **125** items await manual review (field conflicts, possible duplicate systems).

## 2. Research scope

Twenty mandatory seed sources (directories, curated GitHub lists, token tooling and specification, six component libraries, two resource guides, one checklist). Recursion was limited to depth 2–3 from each seed and to the seeds' own domains plus their official machine-readable channels (llms.txt Markdown, registries, GitHub REST API/raw files at pinned commits, npm registry metadata, jsDelivr for published package metadata). Official system documentation linked from directories was recorded as URLs but **not** crawled unless the system is one of S11–S16.

## 3. Source inventory

| ID | Source | Status | Pages ok/attempted | Items | Records | Method |
|---|---|---|---|---|---|---|
| S01 | [Design Systems Surf](https://designsystems.surf/) | inspected | 180/180 | 155 | 3682 | html (server-rendered Framer pages) + sitemap.xml |
| S02 | [Adele by UXPin](https://adele.uxpin.com/) | inspected | 1/1 | 103 | 103 | html table (server-rendered) |
| S03 | [Design Systems Repo](https://designsystemsrepo.com/) | inspected | 6/6 | 208 | 208 | html (static site) |
| S04 | [Storybook Showcase](https://storybook.js.org/showcase) | inspected | 104/104 | 103 | 103 | Next.js __NEXT_DATA__ embedded JSON (catalog + project detail pages) |
| S05 | [Design Systems Directory](https://designsystems.directory/) | inspected_partial | 1/1 | 1 | 1 | html inspection |
| S06 | [Awesome Design Systems (alexpate)](https://github.com/alexpate/awesome-design-systems) | inspected | 5/5 | 151 | 152 | GitHub REST API (metadata, tree) + README at pinned commit |
| S07 | [Awesome Design Systems (klaufel)](https://github.com/klaufel/awesome-design-systems) | inspected | 5/5 | 109 | 110 | GitHub REST API (metadata, tree) + README at pinned commit |
| S08 | [Design Systems (saadeghi)](https://github.com/saadeghi/design-systems) | inspected | 5/5 | 90 | 91 | GitHub REST API (metadata, tree) + README at pinned commit |
| S09 | [Style Dictionary](https://github.com/amzn/style-dictionary) | inspected | 18/18 | 167 | 167 | GitHub REST API + documentation Markdown at pinned commit + npm registry version |
| S10 | [Design Tokens Community Group](https://github.com/design-tokens/community-group) | inspected | 31/32 | 204 | 204 | GitHub REST API + technical-report Markdown at pinned commit + published TR page |
| S11 | [shadcn/ui](https://ui.shadcn.com/) | inspected | 158/163 | 65 | 213 | official registry index (/r/index.json) + registry items + docs Markdown (.md) + llms.txt |
| S12 | [Radix UI Primitives](https://www.radix-ui.com/primitives) | inspected | 39/39 | 35 | 36 | official docs source (radix-ui/website MDX on GitHub, pinned commit); site has no llms.txt |
| S13 | [Base UI](https://base-ui.com/) | inspected | 81/81 | 37 | 80 | official llms.txt index (https://base-ui.com/llms.txt) → per-page Markdown |
| S14 | [React Aria](https://react-spectrum.adobe.com/react-aria/) | inspected | 106/106 | 60 | 104 | official llms.txt index (https://react-aria.adobe.com/llms.txt) → per-page Markdown |
| S15 | [Mantine](https://mantine.dev/) | inspected | 272/272 | 180 | 753 | official llms.txt index (https://mantine.dev/llms.txt) → per-page Markdown |
| S16 | [Ant Design](https://ant.design/) | inspected | 141/141 | 72 | 959 | official llms.txt index (https://ant.design/llms.txt) → per-page Markdown |
| S17 | [The Design System Guide: Resources](https://thedesignsystem.guide/resources) | inspected | 1/1 | 75 | 75 | html (heading-scoped link extraction) |
| S18 | [DesignSystems.com](https://www.designsystems.com/) | inspected | 45/45 | 46 | 46 | html (home + section index pages + article meta) |
| S19 | [Design System Checklist](https://github.com/ardeshireshghi/design-system-checklist) | unavailable_seed__substitute_extracted | 8/14 | 232 | 233 | seed probe; discovered substitute repository via GitHub REST API + raw source files |
| S20 | [Design Systems One](https://www.designsystems.one/design-systems) | inspected | 52/52 | 125 | 797 | html gallery + documented public JSON API (advertised in llms.txt) |

## 4. Methodology

1. **Inventory** – seeds registered with stable IDs; robots.txt read per host (missing robots treated as allow-all per RFC 9309); the crawler identifies itself with a descriptive User-Agent.
2. **Discovery** – sitemaps (Surf), embedded page data (Storybook `__NEXT_DATA__`), llms.txt indexes (shadcn, Base UI, React Aria, Mantine, Ant Design, DesignSystems.one), documented JSON APIs, and GitHub trees.
3. **Extraction** – source-specific adapters (`dskb/adapters/*`). Markdown tables are parsed into typed prop/keyboard/data-attribute arrays; Radix JSX tables are parsed from the official docs MDX.
4. **Politeness & safety** – ≥1 s spacing per host (raised by robots `Crawl-delay`), exponential backoff, response-size cap, disk cache with ETag/Last-Modified revalidation. No authentication, CAPTCHA or paywall was bypassed; no repository code was executed; scraped text is treated as untrusted data.
5. **Normalization** – whitespace, canonical URLs (tracking params removed), framework names, organisation names; source-native API and token names preserved verbatim.
6. **Deduplication** – deterministic entity resolution by documentation host (with path for shared hosts such as github.io) and repository identity; name-only matches are never auto-merged and are queued for review.
7. **Validation** – schema/enum checks, URL syntax, relationship integrity, export round-trip parsing and cross-file count agreement.

## 5. Taxonomy

| ID | Category | Records (primary) |
|---|---|---|
| C01 | Design-System Strategy | 55 |
| C02 | Foundations | 1114 |
| C03 | Design Tokens | 1969 |
| C04 | Component Architecture | 0 |
| C05 | Component Catalog | 3261 |
| C06 | Patterns and Product Workflows | 43 |
| C07 | Accessibility and Inclusive Design | 28 |
| C08 | Documentation and Governance | 187 |
| C09 | Engineering and Tooling | 324 |
| C10 | Theming and Brand Systems | 58 |
| C11 | Cross-Platform Design Systems | 0 |
| C12 | Research and Comparative Analysis | 882 |
| C13 | AI-Ready Design-System Knowledge | 196 |

## 6. Major findings

### 6.1 Discovery sources overlap heavily but each adds unique coverage
Canonical systems by number of corroborating sources: 1 source(s): 374, 2 source(s): 69, 3 source(s): 35, 4 source(s): 13, 5 source(s): 7, 6 source(s): 3, 7 source(s): 8, 8 source(s): 1. Directories differ in what they record: Adele audits engineering attributes, Surf maps foundations/components to official pages, DesignSystems.one publishes editorial breakdowns and an AI-readiness audit, and the Storybook Showcase exposes live Storybook URLs and component counts.

### 6.2 Most commonly documented components (Surf system pages)
Number of distinct systems (of 89 Surf systems that list component links) linking at least one official page in each component family (index-level evidence):

| Family / component | Systems |
|---|---|
| Button | 87 |
| Text input | 85 |
| Checkbox | 83 |
| Progress | 82 |
| Dialog | 82 |
| Radio | 81 |
| Tabs | 79 |
| Menu | 76 |
| Switch | 74 |
| Alert | 74 |
| Tooltip | 70 |
| Table / Data grid | 68 |
| Card | 68 |
| Tag | 65 |
| Pagination | 65 |
| Date & time picker | 63 |
| Select | 62 |
| Navigation | 62 |
| Accordion | 62 |
| Textarea | 61 |

### 6.3 Component libraries

- **shadcn/ui** (component_recipes (copy-in source), v4.22.1): 65 components, 166 documented props, 0 with keyboard tables, 116 tokens extracted.
- **Radix Primitives** (headless_primitives, v1.8.1): 35 components, 656 documented props, 22 with keyboard tables, 0 tokens extracted.
- **Base UI** (headless_primitives, v1.9.0): 37 components, 1582 documented props, 0 with keyboard tables, 0 tokens extracted.
- **React Aria** (headless_components_and_hooks, v1.22.1): 60 components, 12052 documented props, 0 with keyboard tables, 0 tokens extracted.
- **Mantine** (styled_component_library, v9.7.3): 180 components, 5391 documented props, 2 with keyboard tables, 482 tokens extracted.
- **Ant Design** (styled_enterprise_design_system, v6.6.7): 72 components, 2219 documented props, 0 with keyboard tables, 820 tokens extracted.

### 6.4 Tokens

- Token records by system/library: Ant Design: 826, Mantine: 488, shadcn/ui: 122, Linear: 7, Airbnb DLS: 6, Cloudscape: 6, Apple Human Interface Guidelines: 6, Atlassian Design System: 6, Audi UI: 6, BBC GEL: 6, Carbon: 6, Chakra UI: 6.
- Token types (source-native; Ant Design declares TypeScript types such as `string | number`, other values are DTCG-style or inferred and flagged `type_inferred`): color: 529, string: 398, number: 310, unknown: 295, string | number: 69, dimension: 42, Padding<string | number> | undefined: 17, fontWeight: 10, shadow: 5, PaddingInline<string | number> | undefined: 5.
- DTCG `$type` identifiers found in technical-report examples: border, color, cubicBezier, dimension, duration, fontFamily, fontWeight, gradient, number, shadow, strokeStyle, transition, typography.
- Style Dictionary documents 58 predefined transforms, 15 transform groups and 44 formats (e.g. android/colors, android/dimens, android/fontDimens, android/integers, android/resources, android/strings, compose/object, css/fonts.css).

### 6.5 Storybook usage signals

Most common add-ons among showcase projects: @storybook/addon-docs (42), @storybook/addon-a11y (42), @storybook/addon-links (40), chromatic (25), @storybook/addon-actions (12), @storybook/addon-storysource (12), @storybook/addon-viewport (11), storybook-dark-mode (11), @storybook/addon-postcss (8), @storybook/addon-controls (8).

### 6.6 Governance & checklist

Checklist items by area (S19 substitute repository): Core components: 168, Foundations: 26, Design language: 10, Maintenance: 28.

## 7. Accessibility observations

- Headless libraries put accessibility in the primitive: Radix links WAI-ARIA Authoring Practices patterns and publishes keyboard tables per primitive; React Aria documents behaviour, internationalisation and ARIA semantics in prose and API types; Base UI documents accessibility in an overview guide and per-component notes.
- Directory signals about accessibility (Adele 'accessibility guidelines', Surf 'Accessibility' foundation pages) indicate **documentation exists**, not conformance. This dataset never marks a system WCAG-compliant.

## 8. Architecture trade-offs

| Approach | Examples in scope | Gains | Costs |
|---|---|---|---|
| Headless primitives | Radix, Base UI, React Aria | Full visual control; a11y/behaviour solved once | You build and maintain all styling, tokens and docs |
| Copy-in recipes | shadcn/ui | Own the code; no upstream breaking changes; easy token mapping via CSS variables | Upgrades are manual; drift between copies |
| Styled systems | Mantine, Ant Design | Fastest to ship; theming APIs; large component sets | Visual language and API conventions are inherited; deep customisation fights defaults |
| Token pipelines | Style Dictionary + DTCG format | One source → many platforms; spec-aligned interchange | Requires naming governance and CI validation |

## 9. Governance practices observed

- Lifecycle/maturity status, contribution models and RFC discipline appear in editorial breakdowns (S20) and Adele attributes; the checklist (S19) operationalises documentation, local libraries, team process, community support and contribution as discrete checks.
- Changelogs/migration guides are first-class in the libraries (Style Dictionary v4/v5 migration guides; Ant Design and Mantine changelog/migration pages).

## 10. Research-derived recommendations

_These are syntheses across sources, not statements by any single source._

### R1. Author tokens in the DTCG format (`$value`, `$type`, aliases `{group

- **Problem:** Token interchange drifts between design tools and code.
- **Action:** Author tokens in the DTCG format (`$value`, `$type`, aliases `{group.token}`) and compile them with a build tool such as Style Dictionary.
- **Why:** The DTCG technical reports define types, groups and aliasing; Style Dictionary documents DTCG support and multi-platform formats.
- **Evidence:** `spec:s10:token-type-array-aliasing-in-composite-types`, `spec:s10:token-type-string-value`, `spec:s10:token-type-object-value`, `spec:s10:token-type-border`; `tool:s09:concept-dtcg-convert-your-tokens-to-the-dtcg-format`, `tool:s09:concept-dtcg-live-demo`
- **Trade-offs:** Spec features may be ahead of tool support; check the installed version.
- **May not apply when:** Very small single-platform products may not need a pipeline.
- **Verify by:** CI step that parses token files against the DTCG schema and fails on unresolved aliases.

### R2. Standardise `value`/`defaultValue`/`onValueChange` (or the convention of your base library) for every stateful component and document it once

- **Problem:** Inconsistent controlled/uncontrolled APIs across components.
- **Action:** Standardise `value`/`defaultValue`/`onValueChange` (or the convention of your base library) for every stateful component and document it once.
- **Why:** Section 3 of the comparison shows each library is internally consistent but conventions differ across libraries.
- **Evidence:** `cmp:s11:alert-dialog`, `cmp:s12:alert-dialog`, `cmp:s12:dialog`, `cmp:s13:alert-dialog`
- **Trade-offs:** Wrapping a library with different conventions adds an adapter layer.
- **May not apply when:** Not needed if you adopt one library's conventions wholesale.
- **Verify by:** Lint rule or API review checklist item checking prop names.

### R3. Build complex widgets (dialog, combobox, menu, tabs) on headless primitives that publish keyboard tables and ARIA patterns, then test with keyboard and screen readers

- **Problem:** Accessibility regressions in custom widgets.
- **Action:** Build complex widgets (dialog, combobox, menu, tabs) on headless primitives that publish keyboard tables and ARIA patterns, then test with keyboard and screen readers.
- **Why:** Radix and React Aria document keyboard interaction per component; directories show accessibility docs exist widely but do not prove conformance.
- **Evidence:** `cmp:s12:accordion`, `cmp:s12:alert-dialog`, `cmp:s12:checkbox`, `cmp:s12:collapsible`
- **Trade-offs:** Primitives constrain DOM structure; custom styling can still break contrast/focus visibility.
- **May not apply when:** Simple static components gain little.
- **Verify by:** Manual test script per component plus automated axe checks in Storybook.

### R4. Publish per-component status (planned/beta/stable/deprecated), a changelog and migration guides; track the checklist's documentation and release-cycle items

- **Problem:** Teams cannot tell what is ready to use.
- **Action:** Publish per-component status (planned/beta/stable/deprecated), a changelog and migration guides; track the checklist's documentation and release-cycle items.
- **Why:** The checklist's Documentation and Team-process sections and the libraries' migration guides make lifecycle explicit.
- **Evidence:** `gdl:s19:m-documentation-principles`, `gdl:s19:m-documentation-start`, `gdl:s19:m-documentation-design`, `gdl:s19:m-documentation-dev`
- **Trade-offs:** Status labels need an owner to stay accurate.
- **May not apply when:** Early-stage systems with one consumer team.
- **Verify by:** Every component page carries a status; stale-status report in CI.

### R5. Expose machine-readable docs (llms

- **Problem:** AI coding assistants generate off-system UI.
- **Action:** Expose machine-readable docs (llms.txt/Markdown per component, a component registry, DTCG tokens) and keep provenance and versions with each chunk.
- **Why:** Five of the six libraries publish llms.txt or a registry; the Agent-Ready Index audits MCP, llms.txt, DTCG, registry and Code Connect signals.
- **Evidence:** `gdl:s20:ai-ready-carbon-design-mcp`, `gdl:s20:ai-ready-carbon-design-llmstxt`, `gdl:s20:ai-ready-carbon-design-dtcg`
- **Trade-offs:** Machine-readable docs must be regenerated with each release or they mislead.
- **May not apply when:** Internal-only systems without AI tooling.
- **Verify by:** Retrieval test set (e.g. 'which props does Dialog accept?') answered from your docs with citations.

## 11. Limitations

- **S01**: Surf 'Pro' content and signed-in features were not accessed. Component-to-system links are index-level; linked official pages were not inspected by this adapter.
- **S02**: Per-system Adele detail pages were not crawled; the main table carries the same attribute set. Values are Adele's own audit claims and dates are not shown per cell.
- **S04**: Catalog enumerated from the showcase page data (103 projects). Individual Storybook instances (stories, props, variants) were not crawled; doing so requires per-instance inspection.
- **S05**: The site is a Google Programmable Search Engine front-end; its indexed catalogue is not exposed as enumerable pages or data. Results were not scraped (querying Google's CSE programmatically is out of scope). Only site metadata and the claimed count were recorded.
- **S09**: Examples directory READMEs were not decomposed; repository code was not executed.
- **S10**: Meeting notes, issues and discussions were not mined. Maturity is reported from the published TR pages as found; repository Markdown may describe unreleased changes.
- **S12**: Radix docs are read from the official website repository MDX; rendered pages were not scraped. JSX descriptions are flattened to text.
- **S17**: Descriptions are taken from the card text around each link; some source entries have no URL or a mismatched URL (recorded as published).
- **S18**: Article bodies were fetched to verify title/description; full guidance text was not decomposed into individual guideline records (copyrighted editorial content summarised by metadata only).
- **S19**: Seed repository 404. Items were extracted from the discovered repository ardakaracizmeli/design-system-checklist (English translation files), which is the source linked by designsystemchecklist.com.
- Directory-linked official component pages (~thousands of URLs) were recorded but not crawled; their records are `detail_level: index`.
- Data reflects the state of sources on the run date; re-running uses cached responses for up to 7 days and revalidates with ETag/Last-Modified thereafter.

## 12. References

- S01 — Design Systems Surf: https://designsystems.surf/
- S02 — Adele by UXPin: https://adele.uxpin.com/
- S03 — Design Systems Repo: https://designsystemsrepo.com/
- S04 — Storybook Showcase: https://storybook.js.org/showcase
- S05 — Design Systems Directory: https://designsystems.directory/
- S06 — Awesome Design Systems (alexpate): https://github.com/alexpate/awesome-design-systems
- S07 — Awesome Design Systems (klaufel): https://github.com/klaufel/awesome-design-systems
- S08 — Design Systems (saadeghi): https://github.com/saadeghi/design-systems
- S09 — Style Dictionary: https://github.com/amzn/style-dictionary
- S10 — Design Tokens Community Group: https://github.com/design-tokens/community-group
- S11 — shadcn/ui: https://ui.shadcn.com/
- S12 — Radix UI Primitives: https://www.radix-ui.com/primitives
- S13 — Base UI: https://base-ui.com/
- S14 — React Aria: https://react-spectrum.adobe.com/react-aria/
- S15 — Mantine: https://mantine.dev/
- S16 — Ant Design: https://ant.design/
- S17 — The Design System Guide: Resources: https://thedesignsystem.guide/resources
- S18 — DesignSystems.com: https://www.designsystems.com/
- S19 — Design System Checklist: https://github.com/ardeshireshghi/design-system-checklist
- S20 — Design Systems One: https://www.designsystems.one/design-systems
