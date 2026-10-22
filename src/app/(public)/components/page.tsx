import type { Metadata } from 'next'
import Link from 'next/link'
import { X } from 'lucide-react'
import { getItem, getPage, optional } from '@/lib/api/server'
import type { Component, Facet, SystemDetail } from '@/lib/api/types'
import { hrefWith, parseParams, type RawParams } from '@/lib/validation/params'
import { PageIntro } from '@/components/layout/PageIntro'
import { FacetPanel, FilterBar, type FilterGroup, type FilterToggle } from '@/components/catalog/FilterBar'
import { FilterRoot, Results } from '@/components/catalog/FilterState'
import { ComponentCard } from '@/components/catalog/ComponentCard'
import { Stagger, StaggerItem } from '@/components/motion/Reveal'
import { EmptyState, ErrorNotice, RecoveryLink } from '@/components/kit/states'
import { Pagination } from '@/components/kit/pagination'

export const metadata: Metadata = {
  title: 'Component explorer',
  description: 'Every documented component across design systems and libraries — props, variants, keyboard behaviour and accessibility notes, each kept with its own library.',
  alternates: { canonical: '/components' },
}

const SORTS = [
  { value: '', label: 'Most documented' },
  { value: 'name', label: 'Name A–Z' },
  { value: 'library', label: 'Library' },
  { value: 'family', label: 'Family' },
  { value: '-props', label: 'Most props' },
] as const
const PAGE_SIZE = 30

export default async function ComponentsExplorer({ searchParams }: { searchParams: Promise<RawParams> }) {
  const raw = await searchParams
  const p = parseParams(raw, { lists: ['family', 'library'], singles: ['system_id'], flags: ['has_props', 'has_keyboard'], sorts: SORTS.map((s) => s.value).filter(Boolean) })
  const systemId = Number(p.system_id) || undefined
  const [list, facets, system] = await Promise.all([
    getPage<Component>('/components', { query: { ...p, system_id: systemId, page_size: PAGE_SIZE }, tags: ['components'] }).catch((e: Error) => e),
    optional(getItem<Record<string, Facet[]>>('/components/facets', { tags: ['components'] })),
    systemId ? optional(getItem<SystemDetail>(`/design-systems/${systemId}`, { tags: [`system:${systemId}`] })) : null,
  ])
  const groups: FilterGroup[] = [
    { param: 'family', label: 'Category', options: (facets?.families ?? []).map((f) => ({ value: f.value, count: f.count })) },
    { param: 'library', label: 'Design system / library', options: (facets?.libraries ?? []).map((f) => ({ value: f.value, count: f.count })) },
  ]
  const toggles: FilterToggle[] = [
    { param: 'has_props', label: 'Documented props / API' },
    { param: 'has_keyboard', label: 'Keyboard behaviour documented' },
  ]

  return (
    <FilterRoot>
      <PageIntro
        eyebrow="Explorer"
        title="Components"
        accent="across every library."
        description="Every documented component across systems. Each result is one system's own implementation — a Button from one system is never merged with another's — and opens inside that system."
        aside={!(list instanceof Error) && (
          <p className="shrink-0 font-mono text-meta text-muted" aria-live="polite">
            <span className="block text-section font-medium text-text tabular-nums">{list.meta.total_items.toLocaleString()}</span>components match
          </p>
        )}
      />
      <div className="container-page grid gap-10 pt-8 lg:grid-cols-[15rem_minmax(0,1fr)]">
        <aside className="hidden lg:block" aria-label="Filters">
          <div className="sticky top-[calc(var(--header-h)+1.5rem)] max-h-[calc(100svh-var(--header-h)-3rem)] overflow-y-auto pr-2 pb-8">
            <FacetPanel groups={groups} toggles={toggles} />
          </div>
        </aside>
        <div className="flex min-w-0 flex-col gap-8">
          <FilterBar searchPlaceholder="Search components by name, alias or description" groups={groups} toggles={toggles} sorts={[...SORTS]} />
          {systemId && (
            <p className="flex flex-wrap items-center gap-2 text-meta text-text-2">
              Showing components of <Link href={`/systems/${systemId}`} className="focus-ring text-text underline underline-offset-4">{system?.name ?? `system #${systemId}`}</Link>
              <Link href={hrefWith('/components', raw, { system_id: null, page: null })} className="focus-ring inline-flex items-center gap-1 rounded-xs border border-line-strong px-2 py-0.5 text-muted hover:text-text"><X className="size-3" aria-hidden />all systems</Link>
            </p>
          )}
          <Results>
            {list instanceof Error ? <ErrorNotice title="Components could not be loaded" message={list.message} retryHref={hrefWith('/components', raw, {})} />
              : list.data.length === 0 ? <EmptyState title="No components match these filters" action={<RecoveryLink href="/components">Clear filters</RecoveryLink>}>Try a broader search, or remove a filter.</EmptyState>
              : (
                <Stagger as="ul" key={JSON.stringify(raw)} gap={0.03} className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                  {list.data.map((c) => <StaggerItem as="li" key={c.id}><ComponentCard c={c} /></StaggerItem>)}
                </Stagger>
              )}
            {!(list instanceof Error) && <Pagination page={list.meta.page} totalPages={list.meta.total_pages} total={list.meta.total_items} pageSize={PAGE_SIZE} href={(n) => hrefWith('/components', raw, { page: n })} />}
          </Results>
        </div>
      </div>
    </FilterRoot>
  )
}
