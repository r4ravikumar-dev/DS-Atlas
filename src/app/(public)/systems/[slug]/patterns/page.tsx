import type { Metadata } from 'next'
import Link from 'next/link'
import { ArrowRight } from 'lucide-react'
import { getItem, getPage, optional } from '@/lib/api/server'
import { loadSystem, systemOrRedirect } from '@/lib/api/systems'
import type { Guideline } from '@/lib/api/types'
import { hrefWith, parseParams, type RawParams } from '@/lib/validation/params'
import { cn } from '@/lib/cn'
import { EmptyState, ErrorNotice, RecoveryLink } from '@/components/kit/states'
import { Pagination } from '@/components/kit/pagination'

type Props = { params: Promise<{ slug: string }>; searchParams: Promise<RawParams> }
const PAGE_SIZE = 50

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const s = await loadSystem((await params).slug)
  return { title: `${s.name} patterns & guidance`, description: `Patterns, foundations guidance and documentation pages published by ${s.name}.`, alternates: { canonical: `/systems/${s.slug}/patterns` } }
}

/** This system's own documented guidance, grouped by topic. Cross-system research patterns live in the global library. */
export default async function SystemPatterns({ params, searchParams }: Props) {
  const s = await systemOrRedirect((await params).slug, '/patterns')
  const raw = await searchParams
  const p = parseParams(raw, { lists: ['category'] })
  const base = `/systems/${s.slug}`
  const [list, groups] = await Promise.all([
    getPage<Guideline>(`/design-systems/${s.id}/patterns`, { query: { ...p, page_size: PAGE_SIZE }, tags: [`system:${s.id}`] }).catch((e: Error) => e),
    optional(getItem<{ value: string; name: string; count: number }[]>(`/design-systems/${s.id}/pattern-groups`, { tags: [`system:${s.id}`] })),
  ])
  const active = new Set((p.category as string[] | undefined) ?? [])
  if (list instanceof Error) return <ErrorNotice title="Patterns could not be loaded" message={list.message} retryHref={`${base}/patterns`} />
  if (list.meta.total_items === 0 && !active.size) {
    return <EmptyState title={`No patterns or guidance collected for ${s.name}`} action={<RecoveryLink href="/patterns">Browse the pattern library</RecoveryLink>} />
  }
  const byCat = list.data.reduce<Map<string, Guideline[]>>((m, g) => m.set(g.category_name, [...(m.get(g.category_name) ?? []), g]), new Map())
  return (
    <div className="grid gap-10 lg:grid-cols-[15rem_minmax(0,1fr)]">
      <nav aria-label="Topics" className="lg:sticky lg:top-[calc(var(--header-h)+4.5rem)] lg:self-start">
        <p className="eyebrow mb-3">Topics</p>
        <ul className="flex flex-wrap gap-1.5 lg:flex-col lg:gap-0">
          <li><Link href={`${base}/patterns`} aria-current={!active.size ? 'page' : undefined} className={cn('focus-ring flex justify-between gap-2 rounded-xs px-2 py-1 text-[0.86rem]', !active.size ? 'bg-surface-2 text-text' : 'text-text-2 hover:text-text')}>All</Link></li>
          {(groups ?? []).map((g) => (
            <li key={g.value}><Link href={hrefWith(`${base}/patterns`, {}, { category: g.value })} aria-current={active.has(g.value) ? 'page' : undefined}
              className={cn('focus-ring flex justify-between gap-3 rounded-xs px-2 py-1 text-[0.86rem]', active.has(g.value) ? 'bg-surface-2 text-text' : 'text-text-2 hover:text-text')}>{g.name}<span className="font-mono text-[0.68rem] text-faint">{g.count}</span></Link></li>
          ))}
        </ul>
      </nav>
      <div className="flex min-w-0 flex-col gap-12">
        {[...byCat.entries()].map(([cat, items]) => (
          <section key={cat} aria-labelledby={`pc-${cat}`}>
            <h2 id={`pc-${cat}`} className="mb-3 flex items-baseline gap-3 border-b border-line pb-2 text-card font-medium">{cat}<span className="font-mono text-meta text-muted">{items.length}</span></h2>
            <ul className="divide-y divide-line">
              {items.map((g) => (
                <li key={g.id}>
                  <Link href={`${base}/patterns/${g.slug ?? g.id}`} className="focus-ring group flex items-center justify-between gap-4 py-3 hover:text-accent-text">
                    <span className="min-w-0"><span className="block truncate">{g.title.replace(new RegExp(`^${s.name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}:\\s*`), '')}</span>{g.summary && <span className="line-clamp-1 text-meta text-muted">{g.summary}</span>}</span>
                    <ArrowRight className="size-3.5 shrink-0 text-faint transition-transform group-hover:translate-x-0.5" aria-hidden />
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        ))}
        <Pagination page={list.meta.page} totalPages={list.meta.total_pages} total={list.meta.total_items} pageSize={PAGE_SIZE} href={(n) => hrefWith(`${base}/patterns`, raw, { page: n })} />
      </div>
    </div>
  )
}
