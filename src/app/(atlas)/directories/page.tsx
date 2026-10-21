import type { Metadata } from 'next'
import { PageHero } from '@/components/PageHero'
import { Section } from '@/components/Section'
import { Card } from '@/components/Card'
import { TokenDemo } from '@/components/TokenDemo'
import { DIRECTORIES, REPOS } from '@/data/resources'
import grid from '@/components/Section.module.scss'

export const metadata: Metadata = {
  title: 'Directories & repos',
  description: 'Curated design-system directories, GitHub awesome lists, W3C token specs and token build pipelines.',
}

export default function DirectoriesPage() {
  return (
    <>
      <PageHero
        index="03"
        eyebrow="Meta-collections & GitHub"
        title={
          <>
            Search dozens of systems <span className="serif">at once.</span>
          </>
        }
        intro="Aggregators that let you benchmark components across companies, community-maintained awesome lists, and the production tooling behind cross-platform design tokens."
        stats={[
          { value: String(DIRECTORIES.length), label: 'Directories' },
          { value: String(REPOS.length), label: 'Repos & specs' },
        ]}
      />

      <Section
        kicker="01 — Curated directories"
        title={
          <>
            Pick the aggregator for <span className="serif">how you search.</span>
          </>
        }
        intro="Benchmarking a single component? Hunting Figma files? Auditing CSS architecture? Each directory is strongest at one job."
      >
        <div className={grid.grid}>
          {DIRECTORIES.map((d, i) => (
            <Card key={d.name} index={i} title={d.name} href={d.url} desc={d.desc} meta={d.meta} repo={d.repo} accent="var(--sky)" />
          ))}
        </div>
      </Section>

      <Section
        kicker="02 — Awesome lists & token pipelines"
        title={
          <>
            Community lists and <span className="serif">production tooling.</span>
          </>
        }
        intro="Lists maintained through pull requests, plus the specs and build systems that turn one token file into every platform."
      >
        <div className={grid.grid}>
          {REPOS.map((d, i) => (
            <Card key={d.name} index={i} title={d.name} href={d.url} desc={d.desc} meta={d.meta} repo={d.repo} accent="var(--mint)" />
          ))}
        </div>
      </Section>

      <Section
        kicker="03 — Tokens in practice"
        title={
          <>
            Define once, <span className="serif">ship everywhere.</span>
          </>
        }
        intro="A W3C-format token file compiled by Style Dictionary into CSS, SCSS, SwiftUI and Jetpack Compose. Switch outputs to see how aliases resolve."
      >
        <TokenDemo />
      </Section>
    </>
  )
}
