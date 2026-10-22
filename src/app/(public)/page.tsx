import type { Metadata } from 'next'
import Link from 'next/link'
import { ArrowRight, ArrowUpRight } from 'lucide-react'
import { getStats } from '@/lib/api/public'
import { getItem, getPage, optional } from '@/lib/api/server'
import type { Component, Facet, System, Token } from '@/lib/api/types'
import { isColor, tokenValue } from '@/lib/tokens/preview'
import { SITE_DESCRIPTION } from '@/lib/site'
import { Hero } from '@/components/landing/Hero'
import { DiscoveryStory, type StoryNode } from '@/components/landing/DiscoveryStory'
import { SystemCard } from '@/components/catalog/SystemCard'
import { Reveal, Stagger, StaggerItem } from '@/components/motion/Reveal'
import { Button } from '@/components/kit/button'
import { ErrorNotice } from '@/components/kit/states'

export const metadata: Metadata = { description: SITE_DESCRIPTION, alternates: { canonical: '/' } }

/** Libraries in the dataset that publish unstyled, behaviour-only primitives (matched against the live library facet). */
const HEADLESS = ['React Aria', 'Radix Primitives', 'Radix UI', 'Headless UI', 'Ark UI', 'Base UI', 'Ariakit', 'Reach UI', 'Zag', 'Kobalte', 'Melt UI', 'Bits UI']

type Facets = Record<string, Facet[]>

export default async function Home() {
  const [stats, featured, cmpFacets, glFacets, example] = await Promise.all([
    optional(getStats()),
    optional(getPage<System>('/design-systems', { query: { sort: '-sources', page_size: 6 }, tags: ['systems'] })),
    optional(getItem<Facets>('/components/facets', { tags: ['components'] })),
    optional(getItem<Facets>('/guidelines/facets', { tags: ['guidelines'] })),
    optional(storyExample()),
  ])

  const libs = (cmpFacets?.libraries ?? []).filter((l) => HEADLESS.includes(l.value))
  const cat = (code: string) => glFacets?.categories?.find((c) => c.value === code)?.count ?? 0
  const categories = [
    { n: stats?.design_systems, label: 'Design systems', body: 'Complete systems — foundations, components, governance and the links that prove them.', href: '/systems' },
    { n: stats?.components, label: 'Component libraries', body: 'Every documented component, kept separate per library, with props, variants and keyboard notes.', href: '/components' },
    { n: libs.reduce((a, l) => a + l.count, 0), label: 'Headless primitives', body: `Behaviour-only building blocks from ${libs.map((l) => l.value).join(', ') || 'unstyled libraries'}.`, href: `/components?${libs.map((l) => `library=${encodeURIComponent(l.value)}`).join('&')}` },
    { n: stats?.tokens, label: 'Design tokens', body: 'Colour, type, space, radius, elevation and motion — original values, aliases and resolved values.', href: '/tokens' },
    { n: cat('C07'), label: 'Accessibility resources', body: 'Accessibility guidance and checks collected from specifications and system documentation.', href: '/guidelines?category=C07' },
    { n: cat('C09'), label: 'Design-system tooling', body: 'Engineering and tooling: frameworks, build, testing, Storybook, Figma and documentation generation.', href: '/guidelines?category=C09' },
    { n: stats?.storybook_projects, label: 'Storybook showcases', body: 'Public Storybooks with their stories and the component variants extracted from them.', href: '/storybook' },
    { n: cat('C08'), label: 'Governance & checklists', body: 'Documentation, contribution, release and governance practice — plus checklists you can hold a system to.', href: '/guidelines?category=C08' },
  ].filter((c) => (c.n ?? 0) > 0)

  return (
    <>
      <Hero systems={stats?.design_systems ?? null} />

      <section aria-label="What the index holds" className="border-b border-line">
        {stats ? (
          <dl className="container-page grid grid-cols-2 md:grid-cols-5">
            {[
              ['Design systems indexed', stats.design_systems, '/systems'],
              ['Components catalogued', stats.components, '/components'],
              ['Tokens documented', stats.tokens, '/tokens'],
              ['Storybook projects', stats.storybook_projects, '/storybook'],
              ['Sources indexed', stats.sources_indexed ?? null, '/about'],
            ].filter(([, n]) => n !== null).map(([label, n, href], i) => (
              <div key={label as string} className={`border-line py-8 md:py-10 ${i % 2 ? 'border-l pl-5' : ''} md:border-l md:pl-6 md:first:border-l-0 md:first:pl-0 ${i > 1 ? 'border-t md:border-t-0' : ''}`}>
                <dt className="eyebrow mb-3"><Link href={href as string} className="focus-ring hover:text-text">{label}</Link></dt>
                <dd className="text-section font-medium tabular-nums">{(n as number).toLocaleString()}</dd>
              </div>
            ))}
          </dl>
        ) : (
          <div className="container-page py-8"><ErrorNotice title="Live counts are unavailable" backToSite={false} /></div>
        )}
      </section>

      <section aria-labelledby="featured-title" className="container-page py-28">
        <div className="mb-12 flex flex-wrap items-end justify-between gap-6">
          <div className="max-w-2xl">
            <p className="eyebrow mb-4">01 — Most referenced</p>
            <h2 id="featured-title" className="text-title font-medium">Systems the field keeps <span className="font-serif font-normal text-muted italic">pointing to.</span></h2>
            <p className="mt-4 text-text-2">Ranked by how many independent sources list them — not by any editorial judgement.</p>
          </div>
          <Button asChild variant="secondary"><Link href="/systems">All {stats?.design_systems?.toLocaleString() ?? ''} systems <ArrowRight className="size-4" aria-hidden /></Link></Button>
        </div>
        {featured ? (
          <Stagger as="ul" className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {featured.data.map((s) => <StaggerItem as="li" key={s.id}><SystemCard system={s} /></StaggerItem>)}
          </Stagger>
        ) : <ErrorNotice title="Featured systems could not be loaded" retryHref="/" backToSite={false} />}
      </section>

      {categories.length > 0 && (
        <section aria-labelledby="explore-title" className="border-y border-line bg-bg-2">
          <div className="container-page py-28">
            <Reveal className="mb-12 max-w-2xl">
              <p className="eyebrow mb-4">02 — Explore by category</p>
              <h2 id="explore-title" className="text-title font-medium">Start where your question <span className="font-serif font-normal text-muted italic">starts.</span></h2>
            </Reveal>
            <Stagger as="ul" className="grid border-t border-l border-line sm:grid-cols-2 lg:grid-cols-4">
              {categories.map((c, i) => (
                <StaggerItem as="li" key={c.label} className="border-r border-b border-line">
                  <Link href={c.href} className="focus-ring group relative flex h-full min-h-56 flex-col gap-4 p-6 transition-colors duration-300 hover:bg-surface">
                    <span className="flex items-center justify-between font-mono text-meta text-faint">
                      {String(i + 1).padStart(2, '0')}
                      <ArrowUpRight className="size-4 transition-[color,transform] duration-300 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 group-hover:text-accent-text" aria-hidden />
                    </span>
                    <span className="text-card font-medium">{c.label}</span>
                    <span className="text-meta text-muted">{c.body}</span>
                    <span className="mt-auto font-mono text-[1.6rem] tracking-tight text-text tabular-nums">{c.n!.toLocaleString()}</span>
                  </Link>
                </StaggerItem>
              ))}
            </Stagger>
          </div>
        </section>
      )}

      <DiscoveryStory nodes={example ?? FALLBACK_NODES} />

      <section aria-labelledby="cta-title" className="container-page">
        <Reveal className="relative overflow-hidden rounded-lg border border-line bg-surface px-6 py-16 sm:px-14">
          <div aria-hidden className="hairline-grid absolute inset-0 opacity-50 [mask-image:linear-gradient(to_left,black,transparent_70%)]" />
          <div className="relative max-w-2xl">
            <h2 id="cta-title" className="text-title font-medium">Put two systems <span className="font-serif font-normal text-accent-text italic">side by side.</span></h2>
            <p className="mt-4 mb-8 text-text-2">Documented, not documented, or not applicable — the comparison never guesses what a source didn&apos;t say.</p>
            <div className="flex flex-wrap gap-3">
              <Button asChild variant="primary" size="lg"><Link href="/compare">Start a comparison</Link></Button>
              <Button asChild variant="ghost" size="lg"><Link href="/about">How the data is collected</Link></Button>
            </div>
          </div>
        </Reveal>
      </section>
    </>
  )
}

const FALLBACK_NODES: StoryNode[] = [
  { role: 'Design system', label: null, href: '/systems' },
  { role: 'Component', label: null, href: '/components' },
  { role: 'Token', label: null, href: '/tokens' },
  { role: 'Documentation', label: null, href: '/systems' },
  { role: 'Repository', label: null, href: '/systems' },
]

/** A real path for the discovery diagram: a system that has components with documented props, a colour token, docs and a repo. */
async function storyExample(): Promise<StoryNode[] | null> {
  const systems = await getPage<System>('/design-systems', { query: { has_tokens: true, has_components: true, resource: ['official_documentation', 'github_repository'], sort: '-components', page_size: 5 }, tags: ['systems'] })
  for (const s of systems.data) {
    const [comps, toks] = await Promise.all([
      getPage<Component>('/components', { query: { system_id: s.id, has_props: true, page_size: 1 }, tags: ['components'] }),
      getPage<Token>(`/design-systems/${s.id}/tokens`, { query: { page_size: 100 }, tags: ['tokens'] }),
    ])
    const comp = comps.data[0]
    const tok = toks.data.find((t) => isColor(tokenValue(t))) ?? toks.data[0]
    const docs = s.links.find((l) => l.type === 'official_documentation')
    const repo = s.links.find((l) => l.type === 'github_repository')
    if (!comp || !tok || !docs || !repo) continue
    const host = (u: string) => new URL(u).host.replace(/^www\./, '')
    const base = `/systems/${s.slug ?? s.id}`
    return [
      { role: 'Design system', label: s.name, href: base },
      { role: 'Component', label: comp.name, href: comp.slug ? `${base}/components/${comp.slug}` : `/components/${comp.id}` },
      { role: 'Token', label: tok.path, href: tok.slug ? `${base}/tokens/${tok.slug}` : `/tokens/${tok.id}` },
      { role: 'Documentation', label: host(docs.url), href: `${base}/resources` },
      { role: 'Repository', label: new URL(repo.url).pathname.replace(/^\//, ''), href: `${base}/resources` },
    ]
  }
  return null
}
