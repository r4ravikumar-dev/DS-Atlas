# Official Design System Documentation Crawl & Verification Report

**Generated:** 2026-10-21T11:30:55.019485+00:00  
**Platform:** Design Systems Research Platform (DSRP)  
**Status:** 12 priority official design system documentation sources crawled, indexed, and verified with field-level evidence.

## Executive Summary

| Metric | Metric Value | Note |
|---|---|---|
| **Official Sources Registered** | **12** | Selected via citation frequency ranking across independent seed directories |
| **Official Pages Crawled** | **229** | Polite breadth-first crawl respecting robots.txt & domain whitelists |
| **Total Attribute Evidence Records** | **312** | Field-level traceable evidence records with excerpt & source URL |
| **Components Discovered in Official Docs** | **732** | Identified from official component index routes |
| **Systems with Field-Level Evidence** | **12 / 12 (100%)** | All 12 priority systems carry traceable attribute evidence |
| **Verification Standard** | **Partially Verified (Strict)** | No system claimed fully verified without 100% required field groups |

## System Coverage & Verification Matrix

| System Name | Organization | Official URL | Pages Crawled | Components | Verified Req. | Total Attrs | Coverage |
|---|---|---|---|---|---|---|---|
| **Canvas** | Workday | [https://design.workday.com/](https://design.workday.com/) | 20 | 26 | 9/14 | 12 | 64.3% |
| **Carbon** | IBM | [https://www.carbondesignsystem.com/](https://www.carbondesignsystem.com/) | 26 | 76 | 8/14 | 13 | 57.1% |
| **U.S. Web Design System** | U.S. Government | [https://designsystem.digital.gov/](https://designsystem.digital.gov/) | 22 | 77 | 8/14 | 13 | 57.1% |
| **Pajamas** | GitLab | [https://design.gitlab.com/](https://design.gitlab.com/) | 19 | 100 | 7/14 | 11 | 50.0% |
| **Primer** | GitHub | [https://primer.style/](https://primer.style/) | 21 | 130 | 7/14 | 13 | 50.0% |
| **LeafyGreen UI** | MongoDB | [https://www.mongodb.design/](https://www.mongodb.design/) | 16 | 35 | 6/14 | 10 | 42.9% |
| **Polaris** | Shopify | [https://polaris.shopify.com/](https://polaris.shopify.com/) | 20 | 39 | 6/14 | 8 | 42.9% |
| **Atlassian Design System** | Atlassian | [https://atlassian.design/](https://atlassian.design/) | 21 | 115 | 5/14 | 12 | 35.7% |
| **Fluent UI** | Microsoft | [https://fluent2.microsoft.design/](https://fluent2.microsoft.design/) | 20 | 31 | 5/14 | 7 | 35.7% |
| **Material 3** | Google | [https://m3.material.io](https://m3.material.io) | 21 | 27 | 5/14 | 8 | 35.7% |
| **Spectrum** | Adobe | [https://spectrum.adobe.com/](https://spectrum.adobe.com/) | 21 | 40 | 4/14 | 5 | 28.6% |
| **Lightning Design System** | Salesforce | [https://www.lightningdesignsystem.com/2e1ef8501](https://www.lightningdesignsystem.com/2e1ef8501) | 2 | 36 | 1/14 | 1 | 7.1% |

## Attribute Evidence Breakdown

The 312 extracted attribute evidence records span six primary technical dimensions:

1. **Identity & Architecture:**
   * Official documentation root validation (HTTP 200/canonical check)
   * Official source repository discovery (`github.com` / `gitlab.com` verified links)
   * Repository metadata validation via GitHub API (SPDX license, archival status, push activity)

2. **Technical Implementation:**
   * Package distribution (`npm`, `yarn`, `pnpm` install command extractions)
   * Supported frameworks (React, Web Components, Vue, Angular, Svelte) with distinction between explicitly documented support vs package-name inferences

3. **Foundations & Design Tokens:**
   * Color, typography, spacing, layout, elevation, and motion documentation presence
   * Token naming conventions and syntax examples (`--cds-*`, `$color-*`, etc.)

4. **Theming & Color Modes:**
   * Dark mode / theme switching documentation
   * Theme customization APIs

5. **Accessibility (a11y):**
   * Stated accessibility commitments and WCAG target levels (e.g., WCAG 2.1 AA)
   * Keyboard interaction guidelines and focus management documentation

6. **Operations & Governance:**
   * Contribution workflows and component lifecycle processes
   * Migration guides, deprecation policies, and semantic versioning declarations
