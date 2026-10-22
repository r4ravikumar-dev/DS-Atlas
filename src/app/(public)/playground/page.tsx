import type { Metadata } from 'next'
import Link from 'next/link'
import { ArrowRight } from 'lucide-react'
import { getPage } from '@/lib/api/server'
import type { Component } from '@/lib/api/types'
import { PageIntro } from '@/components/layout/PageIntro'
import { ErrorNotice } from '@/components/kit/states'

export const metadata: Metadata = {
  title: 'Interactive playgrounds',
  description: 'Change component properties and see the result — rendered by each design system’s own package where possible.',
  alternates: { canonical: '/playground' },
}

type PgComponent = Component & { slug: string; system_slug: string; system_name: string; playground: 'live' | 'adapter' }

/** Every component with an interactive preview, grouped by its own design system (implementations are never mixed). */
export default async function Playgrounds() {
  const res = await getPage<PgComponent>('/components', { query: { playground: 'any', page_size: 100 }, tags: ['components'] }).catch((e: Error) => e)
  const bySystem = res instanceof Error ? null : res.data.reduce<Map<string, PgComponent[]>>((m, c) => m.set(c.system_slug, [...(m.get(c.system_slug) ?? []), c]), new Map())
  return (
    <>
      <PageIntro eyebrow="Playgrounds" title="Try components" accent="live."
        description="Previews render the system's own package at the version its documentation describes, isolated in a sandboxed frame. Where a system ships as copy-paste source, a clearly labelled preview follows its published recipe and stored tokens." />
      <div className="container-page flex flex-col gap-14 pt-12">
        {!bySystem ? <ErrorNotice title="Playgrounds could not be loaded" message={(res as Error).message} retryHref="/playground" /> : [...bySystem.entries()].map(([slug, items]) => (
          <section key={slug} aria-labelledby={`pg-${slug}`}>
            <div className="mb-4 flex flex-wrap items-baseline justify-between gap-3 border-b border-line pb-2">
              <h2 id={`pg-${slug}`} className="text-card font-medium">{items[0].system_name} <span className="ml-2 text-meta font-normal text-muted">{items[0].playground === 'live' ? 'Live package' : 'Platform preview'}</span></h2>
              <Link href={`/systems/${slug}/playground`} className="focus-ring inline-flex items-center gap-1 text-meta text-accent-text underline decoration-accent/40 underline-offset-4">{items.length} in {items[0].system_name} <ArrowRight className="size-3.5" aria-hidden /></Link>
            </div>
            <ul className="flex flex-wrap gap-2">
              {items.map((c) => (
                <li key={c.id}><Link href={`/systems/${slug}/components/${c.slug}/playground`} className="focus-ring inline-flex h-9 items-center rounded-sm border border-line-strong px-3 text-[0.9rem] transition-colors hover:border-accent hover:bg-accent-soft">{c.name}</Link></li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </>
  )
}
