'use client'

import { Suspense } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useSystemFacets, useSystems } from '@/features/design-systems/api'
import { useUrlState } from '@/hooks/useUrlState'
import { EmptyState, ErrorState, FacetFilter, Missing, PageHeader, Pagination, Panel, SearchInput, Select, SkeletonRows, Tabs, Tag, VerifyBadge } from '@/components/ui'
import { DataTable } from '@/components/ui/DataTable'
import { RESOURCE_LABEL, ResourceLinks } from '@/components/platform/ResourceLinks'
import type { ResourceType } from '@/lib/api/types'
import s from '@/components/platform/page.module.scss'

const PAGE = 24
const RESOURCE_OPTIONS: ResourceType[] = ['official_website', 'official_documentation', 'github_repository', 'figma_file', 'storybook']

function SystemsInner() {
  const u = useUrlState()
  const router = useRouter()
  const view = (u.get('view') || 'grid') as 'grid' | 'table'
  const page = u.getNum('page', 1)
  const q = {
    q: u.get('q'), component: u.get('component'), framework: u.getAll('framework'), platform: u.getAll('platform'), source: u.getAll('source'),
    resource: u.getAll('resource'), verified_resource: u.getAll('verified_resource'), missing_resource: u.get('missing_resource'),
    verification: u.get('verification'), min_sources: u.get('min_sources'), sort: u.get('sort'), page, page_size: PAGE,
  }
  const list = useSystems(q)
  const facets = useSystemFacets()
  const rows = list.data?.data
  const resFacets = (facets.data?.resources ?? []).filter((f) => RESOURCE_OPTIONS.includes(f.value as ResourceType))
  const filtered = Object.entries(q).some(([k, v]) => !['page', 'page_size', 'sort'].includes(k) && (Array.isArray(v) ? v.length > 0 : !!v))
  return (
    <>
      <PageHeader title="Design systems" description="One record per design system, consolidated from every source that lists it. Verified links were confirmed on the system's official pages; others are directory-listed." />
      <div className={s.filters}>
        <SearchInput value={u.get('q')} onChange={(v) => u.set({ q: v })} placeholder="Search name, organization, description…" />
        <SearchInput value={u.get('component')} onChange={(v) => u.set({ component: v })} placeholder="Has component… (e.g. Date picker)" />
        <FacetFilter label="Technology" facets={facets.data?.frameworks} selected={u.getAll('framework')} onChange={(v) => u.set({ framework: v })} />
        <FacetFilter label="Platform" facets={facets.data?.platforms} selected={u.getAll('platform')} onChange={(v) => u.set({ platform: v })} />
        <FacetFilter label="Has resource" facets={resFacets} format={(v) => RESOURCE_LABEL[v as ResourceType]} selected={u.getAll('resource')} onChange={(v) => u.set({ resource: v })} />
        <FacetFilter label="Verified resource" facets={resFacets.map((f) => ({ value: f.value, count: f.verified }))} format={(v) => RESOURCE_LABEL[v as ResourceType]} selected={u.getAll('verified_resource')} onChange={(v) => u.set({ verified_resource: v })} />
        <Select label="Missing resource" value={u.get('missing_resource')} onChange={(v) => u.set({ missing_resource: v })} options={[{ value: '', label: 'Any resources' }, { value: 'official', label: 'Missing official link' }, ...RESOURCE_OPTIONS.map((t) => ({ value: t, label: `Missing ${RESOURCE_LABEL[t].toLowerCase()}` }))]} />
        <FacetFilter label="Listed by source" facets={facets.data?.sources} selected={u.getAll('source')} onChange={(v) => u.set({ source: v })} />
        <Select label="Verification" value={u.get('verification')} onChange={(v) => u.set({ verification: v })} options={[{ value: '', label: 'Any verification' }, { value: 'verified', label: 'Verified' }, { value: 'partially_verified', label: 'Partially verified' }, { value: 'unverified', label: 'Unverified' }]} />
        <Select label="Sort" value={u.get('sort')} onChange={(v) => u.set({ sort: v })} options={[{ value: '', label: 'Most corroborated' }, { value: 'name', label: 'Name A–Z' }, { value: '-components', label: 'Most components' }, { value: '-tokens', label: 'Most tokens' }, { value: '-updated', label: 'Recently updated' }]} />
        <Tabs value={view} onChange={(v) => u.set({ view: v === 'grid' ? null : v }, { resetPage: false })} tabs={[{ value: 'grid', label: 'Grid' }, { value: 'table', label: 'Table' }]} />
        <span className={s.filterMeta} aria-live="polite">{list.data && `${list.data.meta.total_items.toLocaleString()} systems`}</span>
      </div>
      {list.error ? <ErrorState error={list.error} onRetry={() => list.refetch()} /> : !rows ? <SkeletonRows rows={6} cols={3} /> : rows.length === 0 ? (
        <EmptyState title={filtered ? 'No systems match these filters' : 'No design systems in the database yet'}>
          {filtered ? 'Clear a filter to widen the search.' : 'The directory is empty right now.'}
        </EmptyState>
      ) : view === 'grid' ? (
        <div className={s.cards} style={{ opacity: list.isFetching ? 0.6 : 1 }}>
          {rows.map((d) => (
            <article key={d.id} className={s.card} data-testid="system-card">
              <span className={s.org}>{d.organization ?? 'Organization not recorded'}</span>
              <h3><Link href={`/admin/systems/${d.id}`}>{d.name}</Link></h3>
              {d.description ? <p>{d.description}</p> : <Missing label="No description collected" />}
              <ResourceLinks links={d.links} compact />
              <div className={s.counts}>
                <span><b>{d.component_count}</b> components</span>
                <span><b>{d.token_count}</b> tokens</span>
                <span><b>{d.resource_count}</b> links</span>
                <span><b>{d.source_count}</b> sources</span>
              </div>
              <footer>
                <VerifyBadge status={d.verification_status} />
                {d.frameworks.slice(0, 3).map((f) => <Tag key={f}>{f}</Tag>)}
              </footer>
            </article>
          ))}
        </div>
      ) : (
        <Panel>
          <DataTable
            caption="Design systems"
            loading={list.isFetching}
            rows={rows}
            rowKey={(r) => r.id}
            onRowClick={(r) => router.push(`/admin/systems/${r.id}`)}
            sort={u.get('sort')}
            onSort={(k) => u.set({ sort: k })}
            columns={[
              { key: 'name', header: 'System', sortKey: 'name', cell: (r) => <span className={s.cell}><strong>{r.name}</strong><small>{r.organization}</small></span> },
              { key: 'links', header: 'Resources', cell: (r) => <ResourceLinks links={r.links} compact />, hideBelow: 'lg' },
              { key: 'fw', header: 'Technologies', cell: (r) => (r.frameworks.length ? r.frameworks.slice(0, 3).join(', ') : <Missing />), hideBelow: 'md' },
              { key: 'comp', header: 'Components', sortKey: 'components', cell: (r) => r.component_count, align: 'right', hideBelow: 'md' },
              { key: 'tok', header: 'Tokens', sortKey: 'tokens', cell: (r) => r.token_count, align: 'right', hideBelow: 'md' },
              { key: 'src', header: 'Sources', sortKey: 'sources', cell: (r) => r.source_count, align: 'right' },
              { key: 'ver', header: 'Verification', cell: (r) => <VerifyBadge status={r.verification_status} /> },
            ]}
          />
        </Panel>
      )}
      {list.data && list.data.meta.total_items > 0 && <Pagination page={page} pageSize={PAGE} total={list.data.meta.total_items} totalPages={list.data.meta.total_pages} onPage={(p) => u.set({ page: p }, { resetPage: false })} />}
    </>
  )
}

export default function SystemsPage() {
  return <Suspense><SystemsInner /></Suspense>
}
