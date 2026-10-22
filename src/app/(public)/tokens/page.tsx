import type { Metadata } from 'next'
import { Fragment } from 'react'
import Link from 'next/link'
import { ArrowRight } from 'lucide-react'
import { getItem, getPage, optional } from '@/lib/api/server'
import type { Facet, Token } from '@/lib/api/types'
import { hrefWith, parseParams, type RawParams } from '@/lib/validation/params'
import { PageIntro } from '@/components/layout/PageIntro'
import { FacetPanel, FilterBar, type FilterGroup, type FilterToggle } from '@/components/catalog/FilterBar'
import { FilterRoot, Results } from '@/components/catalog/FilterState'
import { TokenSwatch } from '@/components/tokens/TokenPreview'
import { CopyButton } from '@/components/kit/copy-button'
import { EmptyState, ErrorNotice, RecoveryLink } from '@/components/kit/states'
import { Pagination } from '@/components/kit/pagination'

export const metadata: Metadata = {
  title: 'Foundations & design tokens',
  description: 'Inspect design tokens across systems: colour, type, spacing, radius, elevation and motion — original values, alias chains and resolved values, each with its source.',
  alternates: { canonical: '/tokens' },
}

const SORTS = [
  { value: '', label: 'System, then path' },
  { value: 'path', label: 'Token path' },
  { value: 'type', label: 'Type' },
] as const
const PAGE_SIZE = 50

export default async function TokenExplorer({ searchParams }: { searchParams: Promise<RawParams> }) {
  const raw = await searchParams
  const p = parseParams(raw, { lists: ['system', 'type', 'theme', 'platform', 'group'], flags: ['has_alias'], sorts: SORTS.map((s) => s.value).filter(Boolean) })
  const [list, facets] = await Promise.all([
    getPage<Token>('/tokens', { query: { ...p, page_size: PAGE_SIZE }, tags: ['tokens'] }).catch((e: Error) => e),
    optional(getItem<Record<string, Facet[]>>('/tokens/facets', { tags: ['tokens'] })),
  ])
  const opts = (k: string, limit = 60) => (facets?.[k] ?? []).slice(0, limit).map((f) => ({ value: f.value, count: f.count }))
  const groups: FilterGroup[] = [
    { param: 'system', label: 'Design system', options: opts('systems') },
    { param: 'type', label: 'Type', options: opts('types', 20) },
    { param: 'group', label: 'Group', options: opts('groups') },
    { param: 'theme', label: 'Theme', options: opts('themes') },
    { param: 'platform', label: 'Platform', options: opts('platforms') },
  ]
  const toggles: FilterToggle[] = [{ param: 'has_alias', label: 'References another token (alias)' }]

  return (
    <FilterRoot>
      <PageIntro
        eyebrow="Foundations"
        title="Design tokens"
        accent="as each system publishes them."
        description="Original token values exactly as collected, alias relationships, and a resolved value only where the source's own aliases lead to one. Missing values stay missing."
        aside={!(list instanceof Error) && (
          <p className="shrink-0 font-mono text-meta text-muted" aria-live="polite">
            <span className="block text-section font-medium text-text tabular-nums">{list.meta.total_items.toLocaleString()}</span>tokens match
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
          <FilterBar searchPlaceholder="Search token paths, values or descriptions" groups={groups} toggles={toggles} sorts={[...SORTS]} />
          <Results>
            {list instanceof Error ? <ErrorNotice title="Tokens could not be loaded" message={list.message} retryHref={hrefWith('/tokens', raw, {})} />
              : list.data.length === 0 ? <EmptyState title="No tokens match these filters" action={<RecoveryLink href="/tokens">Clear filters</RecoveryLink>}>Try another system or remove a filter.</EmptyState>
              : (
                <div className="focus-ring overflow-x-auto rounded-sm border border-line" tabIndex={0} role="region" aria-label="Tokens table (scrolls horizontally)">
                  <table className="w-full min-w-[44rem] text-left text-meta">
                    <caption className="sr-only">Design tokens</caption>
                    <thead className="border-b border-line bg-surface/60">
                      <tr>{['', 'Token', 'Original value', 'Resolved value', 'Type · theme'].map((h, i) => <th key={i} scope="col" className="px-3 py-2.5 font-normal text-muted">{h}</th>)}</tr>
                    </thead>
                    <tbody className="divide-y divide-line">
                      {list.data.map((t, i) => (
                        <Fragment key={t.id}>
                        {(i === 0 || list.data[i - 1].system_id !== t.system_id) && (
                          <tr className="bg-bg-2"><th colSpan={5} scope="rowgroup" className="px-3 pt-4 pb-2 text-left font-normal">
                            {t.system_slug ? <Link href={`/systems/${t.system_slug}/tokens`} className="focus-ring text-card font-medium text-text hover:text-accent-text">{t.design_system_name}</Link> : <span className="text-card font-medium">{t.design_system_name}</span>}
                          </th></tr>
                        )}
                        <tr className="group hover:bg-surface/50">
                          <td className="w-12 px-3 py-2"><TokenSwatch token={t} className="size-7" /></td>
                          <td className="max-w-[18rem] px-3 py-2">
                            <Link href={t.system_slug && t.slug ? `/systems/${t.system_slug}/tokens/${t.slug}` : `/tokens/${t.id}`} className="focus-ring block truncate font-mono text-text hover:text-accent-text" title={t.path}>{t.path}</Link>
                            {t.alias_of && <span className="block truncate font-mono text-[0.68rem] text-violet">→ {t.alias_of}</span>}
                          </td>
                          <td className="max-w-[14rem] px-3 py-2 font-mono text-text-2">
                            {t.raw_value ? <span className="flex items-center gap-1"><span className="truncate" title={t.raw_value}>{t.raw_value}</span><CopyButton value={t.raw_value} label="Copy value" className="opacity-0 group-hover:opacity-100 focus-visible:opacity-100" /></span> : <span className="text-faint italic">not recorded</span>}
                          </td>
                          <td className="max-w-[10rem] truncate px-3 py-2 font-mono text-text-2">{t.resolved_value ?? <span className="text-faint">—</span>}</td>
                          <td className="px-3 py-2 text-muted">{t.type ?? '—'}{t.theme && t.theme !== 'default' ? ` · ${t.theme}` : ''}</td>
                        </tr>
                        </Fragment>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            {!(list instanceof Error) && <Pagination page={list.meta.page} totalPages={list.meta.total_pages} total={list.meta.total_items} pageSize={PAGE_SIZE} href={(n) => hrefWith('/tokens', raw, { page: n })} />}
          </Results>
          <p className="text-meta text-muted">Looking for one system&apos;s full palette, type scale and spacing? Open it from the <Link href="/systems?has_tokens=true" className="focus-ring text-accent-text underline decoration-accent/40 underline-offset-4 hover:decoration-accent">systems that publish tokens <ArrowRight className="inline size-3.5" aria-hidden /></Link></p>
        </div>
      </div>
    </FilterRoot>
  )
}
