# Storybook Showcase Story Enumeration & Component Variant Coverage Report

**Generated:** 2026-10-21T11:41:23.332318+00:00  
**Platform:** Design Systems Research Platform (DSRP)  
**Scope:** https://storybook.js.org/showcase (103 showcase projects)

## Executive Summary

| Metric | Count | Note |
|---|---|---|
| **Showcase Projects Inventoried** | **103** | Complete showcase catalog reconciled with S04 crawl |
| **Public Storybooks Inspected** | **103** | 100% of projects checked for reachability & discovery |
| **Public Story Indexes Discovered** | **40** | `index.json` (Storybook ≥7) or `stories.json` (6.x) |
| **Verified Stories Extracted** | **17600** | Total public story and documentation entries |
| **Component Stories** | **14491** | Interactive component render states |
| **Autodocs Entries** | **2646** | Auto-generated component documentation pages |
| **Documentation-Only Entries** | **463** | MDX / editorial documentation pages |
| **Component Variants Extracted** | **12150** | Parsed CSF args/argTypes and inferred variants |
| **Stories Linked to Canonical Components** | **728** | Connected by exact name within resolved design system |
| **No Public Index Exposed** | **32** | Static bundle execution required; browser rendering avoided |
| **Unreachable / Inactive Storybooks** | **31** | Host offline, expired deploy, or HTTP error |

## Story & Variant Extraction Methodology

1. **Public Story Discovery Without Guessing:**
   * Storybook deployments are probed for standard metadata endpoints: `index.json` (v3 index schema) and `stories.json` (v2/v1 schema).
   * Raw indices are hashed with SHA-256 and persisted content-addressed in object storage.
   * No URLs are fabricated: IDs originate directly from index entries and format using `?path=/story/{id}`.

2. **CSF Source Parsing (High Confidence):**
   * For projects with verified public GitHub repositories, story CSF sources are fetched from `raw.githubusercontent.com`.
   * Story and component `args` and `argTypes` are parsed into literal Python data structures.
   * `story_args`: **251** variants extracted directly from CSF export arguments.
   * `arg_types_options`: **199** variants extracted from control options.

3. **Story Name Inference (Low Confidence):**
   * When repository sources are unavailable, non-generic story names yield **11700** inferred variants.
   * Explicitly labeled `story_name_inference` with low confidence; never misclassified as verified API capabilities.

## Top Storybook Projects by Extracted Stories

| Project Slug | Title | Organization | Status | Stories | Docs | Variants | Version | Framework |
|---|---|---|---|---|---|---|---|---|
| `clever-cloud-web-components` | Web Components | Clever Cloud | indexed | 1310 | 275 | 1236 | 10.4.0 | @storybook/web-components-vite |
| `adobe-spectrum-web-components` | Spectrum Web Components | Adobe | indexed | 1086 | 161 | 1021 | ≥7 (index v5) | @storybook/web-components-webpack5 |
| `smarthr-smarthr-ui` | SmartHR UI | SmartHR | indexed | 992 | 138 | 847 | 10.5.10 | @storybook/react-vite |
| `wordpress-gutenberg` | Gutenberg | WordPress | indexed | 926 | 283 | 761 | 10.6.1 | @storybook/react-vite |
| `sap-fundamental-styles` | fundamental-styles | SAP | indexed | 798 | 171 | 744 | 10.6.1 | @storybook/html-vite |
| `passbolt-ui-kit` | Passbolt user interface kit | Passbolt | indexed | 627 | 1 | 549 | 10.5.6 | @storybook/react-webpack5 |
| `spaziodati-oniru` | Oniru | Spaziodati | indexed | 575 | 87 | 503 | 10.2.15 | @storybook/react-vite |
| `workday-canvas` | Canvas | Workday | indexed | 553 | 135 | 450 | ≥7 (index v5) | @storybook/react-vite |
| `spaceone-spaceone-design-system` | SpaceONE Design System | SpaceONE | indexed | 513 | 101 | 357 | 7.6.20 | @storybook/vue-vite |
| `carbon-design-system-carbon-components-react` | Carbon Components React | Carbon Design System | indexed | 508 | 135 | 405 | 10.3.5 | @storybook/react-vite |
| `va-design-system` | VA Design System | US Department of Veteran's Affairs | indexed | 487 | 78 | 419 | 10.2.10 | @storybook/react-webpack5 |
| `nasa-jpl-explorer-1` | Explorer 1 | NASA's Jet Propulsion Laboratory | indexed | 478 | 143 | 402 | 10.6.2 | @storybook/vue3-vite |
| `narmi-narmi-design-system` | Narmi Design System | Narmi | indexed | 441 | 86 | 351 | 10.4.6 | @storybook/react-vite |
| `kiwicom-orbit` | orbit | kiwicom | indexed | 397 | 0 | 284 | 8.6.14 | @storybook/react-webpack5 |
| `trendyol-baklava-design-system` | Baklava Design System | Trendyol | indexed | 368 | 57 | 450 | 7.4.3 | @storybook/web-components-vite |
| `launchdarkly-launchpad` | LaunchPad | LaunchDarkly | indexed | 336 | 101 | 243 | 10.2.19 | @storybook/react-vite |
| `grafana-grafana-ui` | Grafana UI | Grafana | indexed | 335 | 145 | 221 | 10.3.6 | @storybook/react-webpack5 |
| `sumup-circuit-ui` | Circuit UI | SumUp | indexed | 295 | 102 | 268 | 10.5.10 | @storybook/react-vite |
| `nivo-nivo` | Nivo | Nivo | indexed | 278 | 42 | 244 | 8.6.12 | @storybook/react-webpack5 |
| `jetbrains-ring-ui` | Ring UI | JetBrains | indexed | 272 | 78 | 219 | 10.6.0 | @storybook/react-webpack5 |
| `storyblok-design-system` | Design System | Storyblok | indexed | 268 | 50 | 204 | 7.6.20 | @storybook/vue3-vite |
| `gilbarbara-components` | Components | @gilbarbara | indexed | 267 | 72 | 181 | 8.5.5 | @storybook/react-vite |
| `telefonica-mistica` | Mistica | Telefonica | indexed | 229 | 0 | 233 | 10.2.19 | @storybook/react-vite |
| `british-gas-nucleus` | Nucleus | British Gas | indexed | 204 | 0 | 201 | — | — |
| `govuk-react` | React | GOV.UK | indexed | 196 | 62 | 151 | 7.6.17 | @storybook/react-webpack5 |

## Inaccessible Projects Summary

* **32 projects** host custom or older Storybook builds that do not publish a static `index.json` or `stories.json`. These require executing client JavaScript in a headless browser, which was omitted to respect access limits.
* **31 projects** were unreachable due to decommissioned subdomains (e.g., Netlify/Heroku ephemeral instances) or DNS failures.
All limitations and failure categories are documented in `storybook_extraction_failures.json`.