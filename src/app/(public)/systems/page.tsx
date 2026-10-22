import type { Metadata } from 'next'
import { getItem, getPage, optional } from '@/lib/api/server'
import type { Facet, System } from '@/lib/api/types'
import { hrefWith, parseParams, type RawParams } from '@/lib/validation/params'
import { PageIntro } from '@/components/layout/PageIntro'
import { FilterBar, FacetPanel, type FilterGroup, type FilterToggle } from '@/components/catalog/FilterBar'
import { FilterRoot, Results } from '@/components/catalog/FilterState'
import { SystemCard } from '@/components/catalog/SystemCard'
import { RESOURCE_META } from '@/components/catalog/resources'
import { Stagger, StaggerItem } from '@/components/motion/Reveal'
import { EmptyState, ErrorNotice, RecoveryLink } from '@/components/kit/states'
import { Pagination } from '@/components/kit/pagination'

export const metadata: Metadata = {
  title: 'Design systems',
  description: 'Browse and filter every indexed design system by framework, official resources, and component and token coverage.',
  alternates: { canonical: '/systems' },
}

const SORTS = [
  { value: '', label: 'Most referenced' },
  { value: 'name', label: 'Name A–Z' },
  { value: '-components', label: 'Most components' },
  { value: '-tokens', label: 'Most tokens' },
  { value: '-updated', label: 'Recently updated' },
] as const

const PAGE_SIZE = 24

interface SystemFacets { frameworks: Facet[]; verification_status: Facet[]; platforms: Facet[]; resources: (Facet & { verified: number })[] }

export default async function SystemsDirectory({ searchParams }: { searchParams: Promise<RawParams> }) {
  const raw = await searchParams
  const p = parseParams(raw, { lists: ['framework', 'resource', 'platform'], singles: ['view'], flags: ['has_tokens', 'has_components'], sorts: SORTS.map((s) => s.value).filter(Boolean) })
  const [list, facets] = await Promise.all([
    getPage<System>('/design-systems', { query: { ...p, view: undefined, page_size: PAGE_SIZE }, tags: ['systems'] }).catch((e: Error) => e),
    optional(getItem<SystemFacets>('/design-systems/facets', { tags: ['systems'] })),
  ])

  const groups: FilterGroup[] = [
    { param: 'resource', label: 'Official resources', options: (facets?.resources ?? []).filter((r) => r.value !== 'additional_resource').map((r) => ({ value: r.value, label: RESOURCE_META[r.value as keyof typeof RESOURCE_META]?.label ?? r.value, count: r.count })) },
    { param: 'framework', label: 'Framework', options: (facets?.frameworks ?? []).map((f) => ({ value: f.value, count: f.count })) },
    { param: 'platform', label: 'Platform', options: (facets?.platforms ?? []).map((f) => ({ value: f.value, count: f.count })) },
  ]
  const toggles: FilterToggle[] = [
    { param: 'has_components', label: 'Has collected components' },
    { param: 'has_tokens', label: 'Has collected design tokens' },
  ]
  const view = raw.view === 'list' ? 'list' : 'grid'

  return (
    <FilterRoot>
      <PageIntro
        eyebrow="Directory"
        title="Design systems"
        accent="in the index."
        description="Every system collected from public directories and official documentation. Filter by what each one actually publishes — official resources, components and tokens."
        aside={!(list instanceof Error) && (
          <p className="shrink-0 font-mono text-meta text-muted" aria-live="polite">
            <span className="block text-section font-medium text-text tabular-nums">{list.meta.total_items.toLocaleString()}</span>
            {list.meta.total_items === 1 ? 'system' : 'systems'} match
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
          <FilterBar searchPlaceholder="Search by name or organisation" groups={groups} toggles={toggles} sorts={[...SORTS]} view />
          <Results>
            {list instanceof Error ? (
              <ErrorNotice title="Design systems could not be loaded" message={list.message} retryHref={hrefWith('/systems', raw, {})} />
            ) : list.data.length === 0 ? (
              <EmptyState title="No design systems match these filters" action={<RecoveryLink href="/systems">Clear filters</RecoveryLink>}>Try removing a filter, or search for a broader term.</EmptyState>
            ) : view === 'list' ? (
              <ul className="border-t border-line">
                {list.data.map((s, i) => <li key={s.id}><SystemCard system={s} variant="list" index={(list.meta.page - 1) * PAGE_SIZE + i + 1} /></li>)}
              </ul>
            ) : (
              <Stagger as="ul" key={JSON.stringify(raw)} className="grid gap-4 sm:grid-cols-2 2xl:grid-cols-3">
                {list.data.map((s) => <StaggerItem as="li" key={s.id}><SystemCard system={s} /></StaggerItem>)}
              </Stagger>
            )}
            {!(list instanceof Error) && (
              <Pagination page={list.meta.page} totalPages={list.meta.total_pages} total={list.meta.total_items} pageSize={PAGE_SIZE} href={(n) => hrefWith('/systems', raw, { page: n })} />
            )}
          </Results>
        </div>
      </div>
    </FilterRoot>
  )
}
