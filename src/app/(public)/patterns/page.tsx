import type { Metadata } from 'next'
import Link from 'next/link'
import { ArrowRight } from 'lucide-react'
import { getItem, getPage, optional } from '@/lib/api/server'
import type { Guideline } from '@/lib/api/types'
import { hrefWith, parseParams, type RawParams } from '@/lib/validation/params'
import { PageIntro } from '@/components/layout/PageIntro'
import { FilterBar, type FilterGroup } from '@/components/catalog/FilterBar'
import { FilterRoot, Results } from '@/components/catalog/FilterState'
import { SystemLogo } from '@/components/system/SystemLogo'
import { EmptyState, ErrorNotice, RecoveryLink } from '@/components/kit/states'
import { Pagination } from '@/components/kit/pagination'

export const metadata: Metadata = {
  title: 'Pattern library',
  description: 'Patterns and guidance organised by the design system that documents them, plus cross-system research checklists and specifications.',
  alternates: { canonical: '/patterns' },
}

interface SystemCount { id: number; slug: string; name: string; organization: string | null; count: number; logo?: { url: string; alt?: string | null } | null }
interface Facets { categories: { value: string; label: string; count: number }[]; kinds: { value: string; count: number }[] }
const PAGE_SIZE = 40

export default async function PatternLibrary({ searchParams }: { searchParams: Promise<RawParams> }) {
  const raw = await searchParams
  const p = parseParams(raw, { lists: ['category', 'kind'] })
  const [systems, research, facets] = await Promise.all([
    optional(getItem<SystemCount[]>('/pattern-library/systems', { tags: ['guidelines'] })),
    getPage<Guideline>('/pattern-library/research', { query: { ...p, page_size: PAGE_SIZE }, tags: ['guidelines'] }).catch((e: Error) => e),
    optional(getItem<Facets>('/pattern-library/facets', { tags: ['guidelines'] })),
  ])
  const groups: FilterGroup[] = [
    { param: 'category', label: 'Topic', options: (facets?.categories ?? []).map((c) => ({ value: c.value, label: c.label, count: c.count })) },
    { param: 'kind', label: 'Kind', options: (facets?.kinds ?? []).map((k) => ({ value: k.value, label: k.value.replace(/_/g, ' '), count: k.count })) },
  ]
  return (
    <>
      <PageIntro eyebrow="Library" title="Patterns" accent="where they are documented."
        description="Each design system's own guidance stays with that system. Research that spans systems — checklists, specifications and component overviews — is kept separately below." />
      <div className="container-page flex flex-col gap-20 pt-12">
        {systems && systems.length > 0 && (
          <section aria-labelledby="by-system">
            <h2 id="by-system" className="mb-6 text-section font-medium">By design system</h2>
            <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {systems.map((s) => (
                <li key={s.id}>
                  <Link href={`/systems/${s.slug}/patterns`} className="focus-ring group flex items-center gap-3 rounded-sm border border-line p-3 transition-colors hover:border-line-strong hover:bg-surface">
                    <SystemLogo name={s.name} logo={s.logo} size="sm" />
                    <span className="min-w-0 flex-1"><span className="block truncate font-medium">{s.name}</span><span className="block text-[0.72rem] text-muted">{s.count} pages of guidance</span></span>
                    <ArrowRight className="size-3.5 shrink-0 text-faint transition-transform group-hover:translate-x-0.5" aria-hidden />
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        )}
        <FilterRoot>
          <section aria-labelledby="research" className="flex flex-col gap-6">
            <div>
              <h2 id="research" className="text-section font-medium">Cross-system research</h2>
              <p className="measure mt-2 text-text-2">Not owned by any single system. Use it to evaluate a system, then check that system&apos;s own documentation.</p>
            </div>
            <FilterBar searchPlaceholder="Search research guidance" groups={groups} />
            <Results>
              {research instanceof Error ? <ErrorNotice title="Research guidance could not be loaded" message={research.message} retryHref={hrefWith('/patterns', raw, {})} />
                : research.data.length === 0 ? <EmptyState title="Nothing matches these filters" action={<RecoveryLink href="/patterns">Clear filters</RecoveryLink>} />
                : (
                  <ul className="divide-y divide-line border-y border-line">
                    {research.data.map((g) => (
                      <li key={g.id}>
                        <Link href={`/${g.record_type === 'pattern' ? 'patterns' : 'guidelines'}/${g.id}`} className="focus-ring group grid gap-1 py-3.5 hover:text-accent-text md:grid-cols-[minmax(0,1fr)_14rem]">
                          <span className="min-w-0"><span className="block truncate">{g.title}</span>{g.summary && <span className="line-clamp-1 text-meta text-muted">{g.summary}</span>}</span>
                          <span className="text-meta text-muted md:text-right">{g.category_name}</span>
                        </Link>
                      </li>
                    ))}
                  </ul>
                )}
              {!(research instanceof Error) && <Pagination page={research.meta.page} totalPages={research.meta.total_pages} total={research.meta.total_items} pageSize={PAGE_SIZE} href={(n) => hrefWith('/patterns', raw, { page: n })} />}
            </Results>
          </section>
        </FilterRoot>
      </div>
    </>
  )
}
