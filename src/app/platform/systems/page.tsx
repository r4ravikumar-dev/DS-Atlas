'use client'

import { Suspense } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { LayoutGrid, List } from 'lucide-react'
import { useSystemFacets, useSystems } from '@/features/design-systems/api'
import { useUrlState } from '@/hooks/useUrlState'
import { ErrorState, ExtLink, FacetFilter, Missing, PageHeader, Pagination, Panel, SearchInput, Select, SkeletonRows, Tabs, Tag, Toggle, VerifyBadge } from '@/components/ui'
import { DataTable } from '@/components/ui/DataTable'
import s from '@/components/platform/page.module.scss'

const PAGE = 24

function SystemsInner() {
  const u = useUrlState()
  const router = useRouter()
  const view = (u.get('view') || 'grid') as 'grid' | 'table'
  const page = u.getNum('page', 1)
  const q = {
    q: u.get('q'), framework: u.getAll('framework'), source: u.getAll('source'), verification: u.get('verification'),
    min_sources: u.get('min_sources'), has_repo: u.get('has_repo') || undefined, has_storybook: u.get('has_storybook') || undefined, sort: u.get('sort'), page, page_size: PAGE,
  }
  const list = useSystems(q)
  const facets = useSystemFacets()
  const rows = list.data?.data
  return (
    <>
      <PageHeader title="Design-system catalog" description="Canonical systems resolved across all sources (documentation host + repository identity). Directory attributes are third-party claims unless verified." />
      <div className={s.filters}>
        <SearchInput value={u.get('q')} onChange={(v) => u.set({ q: v })} placeholder="Search name, organization, description…" />
        <FacetFilter label="Framework" facets={facets.data?.frameworks} selected={u.getAll('framework')} onChange={(v) => u.set({ framework: v })} />
        <FacetFilter label="Listed by source" facets={facets.data?.sources} selected={u.getAll('source')} onChange={(v) => u.set({ source: v })} />
        <Select label="Verification" value={u.get('verification')} onChange={(v) => u.set({ verification: v })} options={[{ value: '', label: 'Any verification' }, { value: 'verified', label: 'Verified' }, { value: 'partially_verified', label: 'Partially verified' }, { value: 'unverified', label: 'Unverified' }]} />
        <Select label="Minimum sources" value={u.get('min_sources')} onChange={(v) => u.set({ min_sources: v })} options={[{ value: '', label: 'Any # of sources' }, { value: '2', label: '≥ 2 sources' }, { value: '3', label: '≥ 3 sources' }, { value: '5', label: '≥ 5 sources' }]} />
        <Toggle label="Has repository" checked={!!u.get('has_repo')} onChange={(v) => u.set({ has_repo: v ? 'true' : null })} />
        <Toggle label="Has Storybook" checked={!!u.get('has_storybook')} onChange={(v) => u.set({ has_storybook: v ? 'true' : null })} />
        <Select label="Sort" value={u.get('sort')} onChange={(v) => u.set({ sort: v })} options={[{ value: '', label: 'Most corroborated' }, { value: 'name', label: 'Name A–Z' }, { value: '-components', label: 'Most components' }, { value: '-tokens', label: 'Most tokens' }]} />
        <Tabs value={view} onChange={(v) => u.set({ view: v === 'grid' ? null : v }, { resetPage: false })} tabs={[{ value: 'grid', label: 'Grid' }, { value: 'table', label: 'Table' }]} />
        <span className={s.filterMeta}>{list.data && `${list.data.meta.total_items.toLocaleString()} systems`}</span>
      </div>
      {list.error ? <ErrorState error={list.error} onRetry={() => list.refetch()} /> : view === 'grid' ? (
        !rows ? <SkeletonRows rows={6} cols={3} /> : rows.length === 0 ? <Panel><p className={s.pad}>No systems match these filters.</p></Panel> : (
          <div className={s.cards} style={{ opacity: list.isFetching ? 0.6 : 1 }}>
            {rows.map((d) => (
              <Link key={d.id} href={`/platform/systems/${d.id}`} className={s.card}>
                <span className={s.org}>{d.organization ?? 'Organization not recorded'}</span>
                <h3>{d.name}</h3>
                {d.description ? <p>{d.description}</p> : <Missing label="No description extracted" />}
                <footer>
                  <VerifyBadge status={d.verification_status} />
                  <Tag>{d.source_count} source{d.source_count === 1 ? '' : 's'}</Tag>
                  {d.component_count > 0 && <Tag>{d.component_count} components</Tag>}
                  {d.token_count > 0 && <Tag tone="accent">{d.token_count} tokens</Tag>}
                  {d.frameworks.slice(0, 2).map((f) => <Tag key={f}>{f}</Tag>)}
                </footer>
              </Link>
            ))}
          </div>
        )
      ) : (
        <Panel>
          <DataTable
            caption="Design systems"
            loading={list.isFetching}
            rows={rows}
            rowKey={(r) => r.id}
            onRowClick={(r) => router.push(`/platform/systems/${r.id}`)}
            sort={u.get('sort')}
            onSort={(k) => u.set({ sort: k })}
            columns={[
              { key: 'name', header: 'System', sortKey: 'name', cell: (r) => <span className={s.cell}><strong>{r.name}</strong><small>{r.organization}</small></span> },
              { key: 'docs', header: 'Documentation', cell: (r) => <ExtLink href={r.documentation_url} />, hideBelow: 'lg' },
              { key: 'fw', header: 'Frameworks', cell: (r) => (r.frameworks.length ? r.frameworks.slice(0, 3).join(', ') : <Missing />), hideBelow: 'md' },
              { key: 'src', header: 'Sources', sortKey: 'sources', cell: (r) => r.source_count, align: 'right' },
              { key: 'comp', header: 'Components', sortKey: 'components', cell: (r) => r.component_count, align: 'right', hideBelow: 'md' },
              { key: 'ver', header: 'Verification', cell: (r) => <VerifyBadge status={r.verification_status} /> },
            ]}
          />
        </Panel>
      )}
      {list.data && <Pagination page={page} pageSize={PAGE} total={list.data.meta.total_items} totalPages={list.data.meta.total_pages} onPage={(p) => u.set({ page: p }, { resetPage: false })} />}
    </>
  )
}

export default function SystemsPage() {
  return <Suspense><SystemsInner /></Suspense>
}
