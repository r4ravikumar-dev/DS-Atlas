import type { Metadata } from 'next'
import Link from 'next/link'
import { getItem, getPage, optional } from '@/lib/api/server'
import { loadSystem, systemOrRedirect } from '@/lib/api/systems'
import type { Token } from '@/lib/api/types'
import { CATEGORY_LABEL, TIER_LABEL } from '@/lib/tokens/labels'
import { hrefWith, parseParams, type RawParams } from '@/lib/validation/params'
import { FacetPanel, FilterBar, type FilterGroup } from '@/components/catalog/FilterBar'
import { FilterRoot, Results } from '@/components/catalog/FilterState'
import { TokenSwatch } from '@/components/tokens/TokenPreview'
import { CopyButton } from '@/components/kit/copy-button'
import { EmptyState, ErrorNotice, RecoveryLink } from '@/components/kit/states'
import { Pagination } from '@/components/kit/pagination'

type Props = { params: Promise<{ slug: string }>; searchParams: Promise<RawParams> }
interface Groups { categories: { value: string; count: number }[]; tiers: { value: string; count: number }[]; themes: { value: string; count: number }[] }
const PAGE_SIZE = 100

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const s = await loadSystem((await params).slug)
  return { title: `${s.name} design tokens`, description: `${s.name}'s design tokens grouped by category and tier, with original values, aliases and resolved values.`, alternates: { canonical: `/systems/${s.slug}/tokens` } }
}

export default async function SystemTokens({ params, searchParams }: Props) {
  const s = await systemOrRedirect((await params).slug, '/tokens')
  const raw = await searchParams
  const p = parseParams(raw, { lists: ['category', 'tier', 'theme'] })
  const base = `/systems/${s.slug}`
  const [list, groups] = await Promise.all([
    getPage<Token>(`/design-systems/${s.id}/tokens`, { query: { ...p, page_size: PAGE_SIZE }, tags: [`system:${s.id}`] }).catch((e: Error) => e),
    optional(getItem<Groups>(`/design-systems/${s.id}/token-groups`, { tags: [`system:${s.id}`] })),
  ])
  const facets: FilterGroup[] = [
    { param: 'category', label: 'Category', options: (groups?.categories ?? []).map((g) => ({ value: g.value, label: CATEGORY_LABEL[g.value] ?? g.value, count: g.count })) },
    { param: 'tier', label: 'Tier', options: (groups?.tiers ?? []).map((g) => ({ value: g.value, label: TIER_LABEL[g.value] ?? g.value, count: g.count })) },
    { param: 'theme', label: 'Theme', options: (groups?.themes ?? []).map((g) => ({ value: g.value, count: g.count })) },
  ]
  const grouped = !(list instanceof Error)
    ? list.data.reduce<Map<string, Token[]>>((m, t) => m.set(t.category ?? 'other', [...(m.get(t.category ?? 'other') ?? []), t]), new Map())
    : null

  if (s.token_count === 0) {
    return <EmptyState title={`No design tokens collected for ${s.name}`} action={<RecoveryLink href={`${base}/components`}>Browse {s.name} components</RecoveryLink>}>Tokens appear when the system publishes them in a machine-readable source the index reads.</EmptyState>
  }
  return (
    <FilterRoot>
      <div className="grid gap-10 lg:grid-cols-[15rem_minmax(0,1fr)]">
        <aside className="hidden lg:block" aria-label="Token groups">
          <div className="sticky top-[calc(var(--header-h)+4.5rem)] max-h-[calc(100svh-var(--header-h)-6rem)] overflow-y-auto pr-2 pb-8"><FacetPanel groups={facets} /></div>
        </aside>
        <div className="flex min-w-0 flex-col gap-8">
          <FilterBar searchPlaceholder={`Search ${s.name} token names and values`} groups={facets} />
          <Results>
            {list instanceof Error ? <ErrorNotice title="Tokens could not be loaded" message={list.message} retryHref={hrefWith(`${base}/tokens`, raw, {})} />
              : list.data.length === 0 ? <EmptyState title="No tokens match these filters" action={<RecoveryLink href={`${base}/tokens`}>Clear filters</RecoveryLink>} />
              : (
                <div className="flex flex-col gap-12">
                  {[...grouped!.entries()].map(([cat, items]) => (
                    <section key={cat} aria-labelledby={`cat-${cat}`}>
                      <h2 id={`cat-${cat}`} className="mb-4 flex items-baseline gap-3 border-b border-line pb-2 text-card font-medium">{CATEGORY_LABEL[cat] ?? cat}<span className="font-mono text-meta text-muted">{items.length}</span></h2>
                      <ul className="divide-y divide-line">
                        {items.map((t) => (
                          <li key={t.id} className="group grid grid-cols-[2.5rem_minmax(0,1fr)] items-center gap-x-4 gap-y-1 py-2.5 md:grid-cols-[2.5rem_minmax(0,1.4fr)_minmax(0,1fr)_8rem]">
                            <TokenSwatch token={t} className="size-7" />
                            <div className="min-w-0">
                              <Link href={`${base}/tokens/${t.slug ?? t.id}`} className="focus-ring block truncate font-mono text-[0.82rem] text-text hover:text-accent-text" title={t.path}>{t.path}</Link>
                              {t.alias_of && <span className="block truncate font-mono text-[0.68rem] text-violet">→ {t.alias_of}</span>}
                            </div>
                            <span className="col-start-2 flex min-w-0 items-center gap-1 font-mono text-[0.78rem] text-text-2 md:col-start-auto">
                              <span className="truncate" title={t.raw_value ?? ''}>{t.resolved_value ?? t.raw_value ?? '—'}</span>
                              {(t.resolved_value ?? t.raw_value) && <CopyButton value={(t.resolved_value ?? t.raw_value)!} label="Copy value" className="opacity-0 group-hover:opacity-100 focus-visible:opacity-100" />}
                            </span>
                            <span className="hidden text-meta text-muted md:block">{[t.tier && TIER_LABEL[t.tier], t.theme && t.theme !== 'default' ? t.theme : null].filter(Boolean).join(' · ')}</span>
                          </li>
                        ))}
                      </ul>
                    </section>
                  ))}
                </div>
              )}
            {!(list instanceof Error) && <Pagination page={list.meta.page} totalPages={list.meta.total_pages} total={list.meta.total_items} pageSize={PAGE_SIZE} href={(n) => hrefWith(`${base}/tokens`, raw, { page: n })} />}
          </Results>
        </div>
      </div>
    </FilterRoot>
  )
}
