# Deduplication report

Generated 2026-10-22T07:13:14+00:00 from the live database (`scripts/export_kb_reports.py`).

| | Before | After |
|---|---:|---:|
| Canonical design systems | 477 | 430 |
| Same-name groups | 35 | 10 |
| Rows in same-name groups | 76 | 22 |
| Systems with neither docs nor repository URL | 102 | 28 |

Net reduction: **47** systems. Recorded alias rows (old key/ID → canonical): **7** (identity_decision: 7).

## How duplicates were found and decided

1. **URL identity (engine).** Records sharing a documentation site key or repository merge automatically. The designsystems.one adapter now reads each entry's detail page, so its 76 name-only entries carry the system's website/repository and merge on that evidence.
2. **Bound sources.** A source registered for a system (official docs crawl, admin intake) always resolves to that system, even if the docs redirect to a new host (this removed the separate `shopify.dev` Polaris entry).
3. **Name collisions → evidence resolver.** Same-name entities are queued as review items and decided with redirect, cross-link, shared repository/Storybook and organization evidence. Same name + different publishing organizations + no shared location ⇒ distinct. A name match alone never merges.

Identity links now: distinct_from 8, implementation_of 10, related_to 11, same_as 42. Latest decision per review item: distinct_system_confirmed 11, duplicate_confirmed 92, linked_resource 10, manual_review_required 5, resolved_existing_system 34. Decisions that rest on a written rationale rather than fetched HTTP evidence: 13.

## Merged records (alias table)

| Old key | Old ID | Name | Canonical key | Reason |
|---|---:|---|---|---|
| `dsys:cisco-momentum-design` | 336 | Momentum Design | `dsys:momentum-design` | identity_decision |
| `dsys:design-liferay-com` | 4268 | Lexicon | `dsys:lexicondesign-io` | identity_decision |
| `dsys:eu-europa-component-library` | 246 | Europa Component Library | `dsys:eu-european-commission-europa-component-library` | identity_decision |
| `dsys:priceline-github-io` | 387 | Priceline One Design System | `dsys:priceline-github-iodesign-system` | identity_decision |
| `dsys:reshaped-reshaped` | 409 | Reshaped | `dsys:reshaped-so` | identity_decision |
| `dsys:shopify-dev` | 3868 | Polaris | `dsys:polaris-shopify-com` | identity_decision |
| `dsys:wix-wix-style-react` | 499 | Wix Style React | `dsys:wix-style-react-com` | identity_decision |

## Still open (needs an administrator decision)

- **Australian Government Design System, Australian Government Design System** (possible_duplicate_system): Australian Government Design System ↔ Australian Government Design System: manual_review_required (Same name but no redirect or cross-reference evidence; may be moved documentation or a fork.)
- **Base Web, base, Base UI** (possible_duplicate_system): Base Web ↔ base: distinct_system_confirmed (Different publishing organizations (Uber vs Mapbox), different locations, no redirect or cross-reference.); Base Web ↔ Base UI: manual_review_required (Same name but no redirect or cross-reference evidence; may be moved documentation or a fork.); base ↔ Base UI: source_unavailable (At least one entity's resources could not be fetched; identity cannot be evaluated.)
- **BLiP, Blip Design System** (possible_duplicate_system): BLiP ↔ Blip Design System: manual_review_required (Same name but no redirect or cross-reference evidence; may be moved documentation or a fork.)
- **Foundation, foundation design system** (possible_duplicate_system): Foundation ↔ foundation design system: manual_review_required (Same name but no redirect or cross-reference evidence; may be moved documentation or a fork.)
- **React95, React95** (possible_duplicate_system): React95 ↔ React95: manual_review_required (Same name but no redirect or cross-reference evidence; may be moved documentation or a fork.)

Remaining same-name groups (distinct systems sharing a name, or awaiting review): australiangovernment, blip, canvas, components, foundation, orbit, react95, solar, styleguide, ui.
