import type { Metadata } from 'next'
import Link from 'next/link'
import { fmtDate, getStats } from '@/lib/api/public'
import { optional } from '@/lib/api/server'
import { Reveal } from '@/components/motion/Reveal'

export const metadata: Metadata = {
  title: 'Methodology',
  description: 'Where the directory’s data comes from, how records are organised and deduplicated, and how the daily synchronisation keeps them current.',
  alternates: { canonical: '/about' },
}

const STEPS = [
  { t: 'Collect', b: 'Public design-system directories, awesome-lists, specifications and each system’s own documentation, packages and Storybooks are crawled politely: robots.txt is honoured, every host is rate-limited and every fetched page is kept as a snapshot.' },
  { t: 'Normalise', b: 'Each source’s records keep their original wording. Component names are mapped to a family (e.g. “Dialog”) as an added, documented normalisation — the source-native name is never replaced.' },
  { t: 'Deduplicate', b: 'Listings are grouped by documentation site and repository. A shared name alone never merges two systems; redirects, cross-links, shared repositories and organisations are the evidence. Merged ids redirect to the canonical record.' },
  { t: 'Verify', b: 'Each system’s official page is fetched and the links it publishes — repository, Figma, Storybook — are confirmed. URLs are never constructed or guessed; a repository counts only with ownership evidence.' },
  { t: 'Keep current', b: 'Once a day every source is re-checked with conditional requests. Unchanged content is not rewritten; a failing source never hides existing data. What changed, and when, is recorded per record.' },
]

export default async function About() {
  const stats = await optional(getStats())
  return (
    <>
      <header className="border-b border-line">
        <div className="container-page pt-14 pb-12 md:pt-20">
          <p className="eyebrow mb-4">Methodology</p>
          <h1 className="max-w-4xl text-title font-medium">Every claim keeps <span className="font-serif font-normal text-muted italic">the source that made it.</span></h1>
          <p className="measure mt-6 text-lg text-text-2">
            The directory is an independent research index. It doesn&apos;t rate systems, and it doesn&apos;t fill gaps: when a source says nothing, the record says
            “not documented” — which means unknown, not unsupported.
          </p>
        </div>
      </header>

      <section aria-labelledby="pipeline" className="container-page py-20">
        <h2 id="pipeline" className="sr-only">How records are made</h2>
        <ol className="grid gap-px overflow-hidden rounded-sm border border-line bg-line md:grid-cols-5">
          {STEPS.map((s, i) => (
            <Reveal as="li" key={s.t} delay={i * 0.05} className="flex flex-col gap-3 bg-bg p-6">
              <span className="font-mono text-meta text-accent-text">{String(i + 1).padStart(2, '0')}</span>
              <span className="text-card font-medium">{s.t}</span>
              <span className="text-[0.9rem] leading-relaxed text-text-2">{s.b}</span>
            </Reveal>
          ))}
        </ol>
      </section>

      <section aria-labelledby="fresh" className="container-page grid gap-12 border-t border-line py-20 lg:grid-cols-2">
        <div>
          <h2 id="fresh" className="text-section font-medium">Freshness</h2>
          <p className="measure mt-4 text-text-2">
            “Checked” moves every day; “content changed” only moves when a source actually published something new. Pages refresh their cached data after a sync
            that changed content, and at most every few minutes otherwise.
          </p>
        </div>
        {stats ? (
          <dl className="grid grid-cols-2 gap-px overflow-hidden rounded-sm border border-line bg-line">
            {[
              ['Sources checked', fmtDate(stats.last_sync_at) ?? '—'],
              ['Content last changed', fmtDate(stats.content_updated_at) ?? '—'],
              ['Sources contributing', stats.sources_indexed?.toLocaleString() ?? '—'],
              ['Design systems', stats.design_systems.toLocaleString()],
              ['Systems with a GitHub repository', stats.systems_with_github.toLocaleString()],
              ['Systems with a Figma file', stats.systems_with_figma.toLocaleString()],
            ].map(([k, v]) => (
              <div key={k} className="bg-bg p-5"><dt className="eyebrow mb-2">{k}</dt><dd className="text-card font-medium tabular-nums">{v}</dd></div>
            ))}
          </dl>
        ) : <p className="text-meta text-muted">Live figures are unavailable right now.</p>}
      </section>

      <section className="container-page border-t border-line pt-20">
        <h2 className="text-section font-medium">Limits worth knowing</h2>
        <ul className="measure mt-6 flex list-disc flex-col gap-3 pl-5 text-text-2">
          <li>Logos and preview images are shown only when a system&apos;s own official site publishes them; otherwise a typographic monogram is used. They are referenced at their original address, not copied.</li>
          <li>Component and token depth depends on what each system publishes in machine-readable form; many systems only expose documentation pages.</li>
          <li>Interactive previews render a system&apos;s own published package only where it can be installed at the documented version; a few are clearly labelled platform-rendered previews. Everything else is documentation only.</li>
          <li>Names and trademarks belong to their owners; listing a system doesn&apos;t imply affiliation or endorsement.</li>
        </ul>
        <p className="mt-10 text-meta text-muted">Questions about a record? Each detail page links to the exact sources and evidence behind it — start from <Link href="/systems" className="focus-ring text-accent-text underline decoration-accent/40 underline-offset-4 hover:decoration-accent">the directory</Link>.</p>
      </section>
    </>
  )
}
