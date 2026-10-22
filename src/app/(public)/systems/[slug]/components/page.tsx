import type { Metadata } from 'next'
import Link from 'next/link'
import { getItem, getPage, optional } from '@/lib/api/server'
import { loadSystem, systemOrRedirect } from '@/lib/api/systems'
import type { Component } from '@/lib/api/types'
import { hrefWith, parseParams, type RawParams } from '@/lib/validation/params'
import { cn } from '@/lib/cn'
import { FilterBar, type FilterGroup, type FilterToggle } from '@/components/catalog/FilterBar'
import { FilterRoot, Results } from '@/components/catalog/FilterState'
import { ComponentCard } from '@/components/catalog/ComponentCard'
import { EmptyState, ErrorNotice, RecoveryLink } from '@/components/kit/states'
import { Pagination } from '@/components/kit/pagination'

type Props = { params: Promise<{ slug: string }>; searchParams: Promise<RawParams> }
interface FamilyGroup { name: string; count: number; families: { name: string; slug: string; count: number; with_playground: number }[] }
const PAGE_SIZE = 60
const SORTS = [{ value: '', label: 'By family' }, { value: 'name', label: 'Name A–Z' }, { value: '-props', label: 'Most documented props' }] as const

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const s = await loadSystem((await params).slug)
  return { title: `${s.name} components`, description: `Every component documented by ${s.name}, organised by family, with props, variants and interactive previews where available.`, alternates: { canonical: `/systems/${s.slug}/components` } }
}

export default async function SystemComponents({ params, searchParams }: Props) {
  const s = await systemOrRedirect((await params).slug, '/components')
  const raw = await searchParams
  const p = parseParams(raw, { lists: ['family'], singles: ['playground'], flags: ['has_props'], sorts: SORTS.map((x) => x.value).filter(Boolean) })
  const base = `/systems/${s.slug}`
  const [list, families] = await Promise.all([
    getPage<Component>(`/design-systems/${s.id}/components`, { query: { ...p, playground: p.playground === 'any' ? 'any' : undefined, page_size: PAGE_SIZE }, tags: [`system:${s.id}`] }).catch((e: Error) => e),
    optional(getItem<FamilyGroup[]>(`/design-systems/${s.id}/component-families`, { tags: [`system:${s.id}`] })),
  ])
  const selected = new Set(Array.isArray(raw.family) ? raw.family : raw.family ? [raw.family] : [])
  const groups: FilterGroup[] = [{ param: 'family', label: 'Family', options: (families ?? []).flatMap((g) => g.families.map((f) => ({ value: f.name, count: f.count }))) }]
  const toggles: FilterToggle[] = [{ param: 'playground', label: 'Has an interactive preview', value: 'any' }, { param: 'has_props', label: 'Documented props / API' }]
  const byFamily = !(list instanceof Error) && !p.sort
    ? list.data.reduce<Map<string, Component[]>>((m, c) => m.set(c.family ?? 'Other components', [...(m.get(c.family ?? 'Other components') ?? []), c]), new Map())
    : null

  return (
    <FilterRoot>
      <div className="grid gap-10 lg:grid-cols-[15rem_minmax(0,1fr)]">
        <aside aria-label="Component families" className="hidden lg:block">
          <div className="sticky top-[calc(var(--header-h)+4.5rem)] max-h-[calc(100svh-var(--header-h)-6rem)] overflow-y-auto pr-2 pb-8">
            <Link href={`${base}/components`} className={cn('focus-ring mb-4 block text-[0.9rem]', selected.size ? 'text-muted hover:text-text' : 'text-text')}>All components <span className="font-mono text-[0.7rem] text-faint">{s.component_count}</span></Link>
            {(families ?? []).map((g) => (
              <div key={g.name} className="mb-5">
                <p className="eyebrow mb-2">{g.name}</p>
                <ul className="flex flex-col">
                  {g.families.map((f) => (
                    <li key={f.slug}>
                      <Link href={hrefWith(`${base}/components`, {}, { family: f.name })} aria-current={selected.has(f.name) ? 'page' : undefined}
                        className={cn('focus-ring flex items-center justify-between gap-2 rounded-xs px-2 py-1 text-[0.86rem]', selected.has(f.name) ? 'bg-surface-2 text-text' : 'text-text-2 hover:text-text')}>
                        {f.name}<span className="font-mono text-[0.68rem] text-faint">{f.count}</span>
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </aside>
        <div className="flex min-w-0 flex-col gap-8">
          <FilterBar searchPlaceholder={`Search ${s.name} components`} groups={groups} toggles={toggles} sorts={[...SORTS]} />
          <Results>
            {list instanceof Error ? <ErrorNotice title="Components could not be loaded" message={list.message} retryHref={hrefWith(`${base}/components`, raw, {})} />
              : list.data.length === 0 ? <EmptyState title={`No ${s.name} components match`} action={<RecoveryLink href={`${base}/components`}>Clear filters</RecoveryLink>}>Try another family or remove a filter.</EmptyState>
              : byFamily ? (
                <div className="flex flex-col gap-12">
                  {[...byFamily.entries()].map(([fam, items]) => (
                    <section key={fam} aria-labelledby={`fam-${fam}`}>
                      <h2 id={`fam-${fam}`} className="mb-4 flex items-baseline gap-3 border-b border-line pb-2 text-card font-medium">{fam}<span className="font-mono text-meta text-muted">{items.length}</span></h2>
                      <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">{items.map((c) => <li key={c.id}><ComponentCard c={c} showSystem={false} /></li>)}</ul>
                    </section>
                  ))}
                </div>
              ) : <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">{list.data.map((c) => <li key={c.id}><ComponentCard c={c} showSystem={false} /></li>)}</ul>}
            {!(list instanceof Error) && <Pagination page={list.meta.page} totalPages={list.meta.total_pages} total={list.meta.total_items} pageSize={PAGE_SIZE} href={(n) => hrefWith(`${base}/components`, raw, { page: n })} />}
          </Results>
        </div>
      </div>
    </FilterRoot>
  )
}
