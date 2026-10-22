# Public experience: design architecture and motion conventions

This document covers the public directory's frontend under `src/app/(public)`. The administration area
(`src/app/admin`) keeps its SCSS-module component library (`src/components/ui`, `src/components/platform`). Both areas
read the same semantic design tokens.

## Art direction

* **Identity.** The look is editorial and research-led. It builds on the product's existing identity: deep ink
  surfaces, one controlled lime accent, and secondary hues (violet, sky, mint, amber, coral) used only for data.
* **Type.** Display moments pair Geist with italic Instrument Serif (for example, *"component by component."*). Metadata
  uses monospace eyebrows (`01 — Most referenced`).
* **Layout.** Hairline rules and grids replace heavy cards. Cards are kept for the directory, where they work as
  "index cards". Radii stay small (4–14 px), and there are no decorative blobs or glass on every surface. Translucency
  is used only on the sticky header and the in-page index, where it improves legibility.
* **System identity.** `system/SystemLogo.tsx` shows the icon a system's official site publishes, referenced at its
  original URL on a neutral white plate. Without one — or if it fails to load — a typographic monogram (initials on a
  tint derived from the name) is used. The overview shows the system's own share image (og:image) with an attribution
  caption. Nothing is borrowed from another system and nothing is invented.
* **No internal status in public UI.** Verification, confidence, crawl and review states are never shown publicly (the
  API omits them); missing resources are simply not listed. Status stays visible in the admin area.

## Tokens (`src/styles/tokens.css`)

1. **Primitives** (`--ink-*`, `--paper-*`, `--lime-*`, `--violet-400/600`, …). These are raw values and are never used
   directly in components.
2. **Semantic tokens.** Examples: `--bg`, `--surface`, `--surface-2`, `--line`, `--text`, `--muted`, `--faint`,
   `--accent`, `--accent-text`, `--success`, `--warning`, `--danger`, plus type, shape, layout and motion tokens.
   * They are redefined under `:root[data-theme='light']`.
   * The light-theme `-600` primitives were chosen to reach at least 4.5:1 contrast on paper and on white.
   * `--faint` is still at least 4.5:1, so it can be used for text.
3. **Tailwind theme** (`src/styles/tailwind.css`) maps the semantic tokens to utilities such as `bg-surface`,
   `text-muted`, `border-line`, `text-display` and `rounded-sm`.
   * Tailwind's default palette and fonts are removed (`--color-*: initial`), so components can't reach for an
     arbitrary colour.
   * Tailwind's preflight is **not** loaded. The element reset lives in `globals.scss` inside `@layer base`, which keeps
     the admin SCSS modules unaffected. Utilities always win over the base layer.

| Type token | Use |
|---|---|
| `text-display` | Landing headline only |
| `text-title` | Page titles |
| `text-section` | Section headings and large numbers |
| `text-card` | Card and entity titles |
| `text-meta` / `text-caption` | Metadata and eyebrows |
| `font-mono` + `text-code` | Token names, props, values and source keys |

## Components

| Folder | Contents |
|---|---|
| `components/kit` | shadcn-style primitives on Radix: `button` (cva variants, `asChild`), `badge`, `verification`, `sheet` (Radix Dialog), `tooltip`, `copy-button`, `code-block`, `external-link`, `pagination` (link-based, crawlable), `states` (empty / error / not documented), `skeleton` |
| `components/navigation` | `SiteHeader` (shared-layout active indicator, Resources popover, ⌘K / `/` search, mobile sheet), `CommandSearch` (combobox / listbox over `/search`), `Wordmark`, `nav.ts` |
| `components/layout` | `SiteFooter` (server; freshness from `/stats`), `PageIntro`, `MotionToggle` |
| `components/catalog` | `SystemCard`, `ComponentCard`, `Monogram`, `ResourceIndicators`, `FilterRoot` / `Results` / `FilterBar` / `FacetPanel` (URL-state filters) |
| `components/details` | `SectionIndex` (sticky scroll-spy), `Section`, `FoundationsViz`, `PropsExplorer`, `ResourcePanel`, `ResourceActions`, `AdminShortcut` |
| `components/tokens` | `TokenSwatch` (colour, radius, spacing, type, weight, family, shadow, duration and easing samples) |
| `components/system` | `SystemLogo`, `SystemTabs` (the per-system workspace navigation) |
| `components/playground` | `Playground` (schema-driven controls, isolated preview frame, theme and viewport switches, reset, configuration and code view) |
| `components/comparison` | `ComparisonMatrix` (difference highlighting, "only differences", API overlap) |
| `components/motion` | `Reveal`, `Stagger` / `StaggerItem`, `Lift` |
| `components/landing` | `Hero` (server-rendered, GET search form), `HeroIllustration` (design-system specimen sheet), `DiscoveryStory` (GSAP ScrollTrigger) |

The whole card is clickable through a stretched title link, which gives one tab stop and no nested links. Status is
always shown as icon plus words, never colour alone.

## Rendering and data

* **Server Components** render every data page: home, `/systems`, `/systems/[id]`, `/components`,
  `/components/[id]`, `/tokens`, `/tokens/[id]`, `/search` and `/about`.
  * They read the backend directly through `lib/api/server.ts`. This module is server-only, and the backend URL never
    reaches the browser.
  * Responses use Next's data cache (`revalidate: 300`) with tags: `public`, `stats`, `systems`, `components`, `tokens`,
    `system:<id>` and so on.
* **Client islands** cover the interactive parts only: filters, search dialog, props filter, section index, compare
  workspace, copy buttons, motion and 3D.
* **URL state.** Filters, sort, view and page live in the URL, so they're shareable. `FilterRoot` pushes the new URL
  inside a transition, and `Results` dims while the server re-renders.
* **Untrusted URL params** are parsed by `lib/validation/params.ts` (zod). Unknown sort keys fall back to the default,
  and malformed values are dropped.
* **Freshness.** After a build that changed content, the backend posts the affected tags to `/revalidate`.
  * The request is authenticated with `REVALIDATE_SECRET` (`services/frontend_cache.py`).
  * A sync where nothing changed sends nothing, so nothing on the site appears to change.
  * The 5-minute revalidation window bounds staleness anyway.
* **Failure handling.** A failed request renders an `ErrorNotice`. It is never replaced with placeholder content.
  Optional sections fail on their own, without taking down the rest of the page.
* **No invented data.**
  * Token previews only draw values that are valid CSS of the expected kind (`lib/tokens/preview.ts`). A unitless `4`
    is never treated as pixels.
  * Variant value sets are read only from union-of-literal prop types (`lib/components/axes.ts`).
  * The props signature is labelled "generated from the documented API".
  * Comparisons show `documented`, `not documented`, `not inspected` (the docs page was never parsed) or
    `not applicable`. Missing data is never shown as "unsupported".

## Motion

**One timing language.** `src/lib/motion/tokens.ts` (mirrored as `--dur-*` and `--ease-*` in `tokens.css`) defines:
* durations `instant` / `fast` / `base` / `slow` / `hero`;
* easings `out`, `inOut`, `emphasized` (with GSAP equivalents);
* springs `snappy` (toggles, indicators), `gentle` (cards, sheets) and `layout`;
* stagger, distance and hover values;
* `viewport` and `viewportList` reveal thresholds.

Which tool to use:

| Tool | Used for |
|---|---|
| **Motion for React** (`motion/react`) | Every interface transition: nav and section-index active indicators (`layoutId`), sheet and dialog springs, search-result highlight, filter chips, view toggle, matrix row changes, copy feedback, card lift (`Lift`), small scroll reveals (`Reveal` / `Stagger`) |
| **GSAP** + `@gsap/react` | One choreographed sequence only — the discovery story: CSS `position: sticky` (no scroll hijacking, no pinning), with ScrollTrigger scrubbing the SVG connections on wide screens. It is scoped with `useGSAP({ scope })`, use `gsap.matchMedia` for breakpoints, and revert on unmount. |
| **CSS** | Hover colours, token duration and easing samples, popover entrance |

**Loading.**
* The hero is static HTML and CSS: a minimal headline and search beside an illustration of what the index catalogues — colour tokens, a type scale, spacing and component states — drawn in the site's own tokens. It rises once on load; nothing animates continuously. (A WebGL particle scene was tried and removed: decorative, unrelated to the content, and about 240 KB of JavaScript.)
* GSAP ScrollTrigger loads only on the landing page.

**Reduced motion.**
* The OS `prefers-reduced-motion` setting and the footer **Reduce motion** switch (`data-motion="reduce"`, stored per
  visitor) are honoured everywhere:
  * `<MotionConfig reducedMotion>` removes transforms and keeps opacity.
  * GSAP timelines don't run, so content is simply there.
  * The 3D scene isn't loaded; the SVG fallback is used.
  * CSS animations and transitions are neutralised.
* `useMotionPreference()` returns `pending` until mount, so server HTML and the first client render agree.

**Lenis smooth scrolling** isn't used. Native scrolling, keyboard scrolling and in-page anchors already work with the
sticky story section, so Lenis would add risk without improving the art direction.

## Accessibility checklist (verified)

* **Automated audit.** axe-core, WCAG 2.0/2.1/2.2 A and AA rule sets, in both themes. It reports no violations on:
  * `/`, `/systems`, `/systems/[id]`, `/components`, `/components/[id]`, `/tokens`, `/tokens/[id]`;
  * `/compare` (with a selection), `/search`, `/about`.
  * A jsdom axe test is part of `npm test`.
* **Keyboard.**
  * A skip link comes first.
  * Visible focus rings come from the `focus-ring` utility.
  * The search dialog is a combobox over a listbox (arrow keys and Enter), with focus trapped by Radix.
  * Sheets close with Escape.
  * Horizontally scrolling tables are focusable regions.
* **Semantics.** One `h1` per page. Sections are labelled. Pagination is a `nav`. Breadcrumbs carry `aria-current`.
  Live result counts use `aria-live`.
* **Colour.** Verification, resource availability and comparison states always pair an icon with text.

## Measured (local production build, unthrottled)

| Route | TTFB | FCP | LCP | CLS |
|---|---|---|---|---|
| `/` (prerendered, revalidates every 5 min) | 15 ms | 68 ms | 108 ms | 0.002 |
| `/systems/2` (dynamic, data-cached) | 108 ms | 148 ms | 780 ms before the header fade was removed from the LCP area | 0.002 |

* **First-load JavaScript** is about 280 KB gzip on most pages and 328 KB on `/` (GSAP included).
  * The React and Next.js runtime account for about 160 KB of that.

Re-measure on a deployed preview with throttling before treating these numbers as production figures.
