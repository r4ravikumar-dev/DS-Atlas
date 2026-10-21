'use client'

import { Suspense } from 'react'
import { useRouter } from 'next/navigation'
import { useComponentFacets, useComponents } from '@/features/components/api'
import { useUrlState } from '@/hooks/useUrlState'
import { ErrorState, FacetFilter, Missing, PageHeader, Pagination, Panel, SearchInput, Select, Tag, Toggle, VerifyBadge } from '@/components/ui'
import { DataTable } from '@/components/ui/DataTable'
import s from '@/components/platform/page.module.scss'

const LEVEL: Record<string, string> = { api: 'Structured API', doc: 'Docs page', index: 'Directory link', editorial_highlight: 'Editorial note' }

function ComponentsInner() {
  const u = useUrlState()
  const router = useRouter()
  const page = u.getNum('page', 1)
  const q = {
    q: u.get('q'), family: u.getAll('family'), library: u.getAll('library'), detail_level: u.getAll('detail_level'),
    has_keyboard: u.get('has_keyboard') || undefined, has_props: u.get('has_props') || undefined, sort: u.get('sort'), page, page_size: 25,
  }
  const list = useComponents(q)
  const facets = useComponentFacets()
  return (
    <>
      <PageHeader title="Component explorer" description="One record per documented component. ‘Structured API’ records carry props, keyboard tables and accessibility notes parsed from official docs; ‘Directory link’ records only prove a system documents the component at a URL." />
      <div className={s.filters}>
        <SearchInput value={u.get('q')} onChange={(v) => u.set({ q: v })} placeholder="Search name or description…" />
        <FacetFilter label="Family" facets={facets.data?.families} selected={u.getAll('family')} onChange={(v) => u.set({ family: v })} />
        <FacetFilter label="Library" facets={facets.data?.libraries} selected={u.getAll('library')} onChange={(v) => u.set({ library: v })} />
        <FacetFilter label="Detail level" facets={facets.data?.detail_levels} selected={u.getAll('detail_level')} onChange={(v) => u.set({ detail_level: v })} format={(v) => LEVEL[v] ?? v} />
        <Toggle label="Has props" checked={!!u.get('has_props')} onChange={(v) => u.set({ has_props: v ? 'true' : null })} />
        <Toggle label="Keyboard documented" checked={!!u.get('has_keyboard')} onChange={(v) => u.set({ has_keyboard: v ? 'true' : null })} />
        <Select label="Sort" value={u.get('sort')} onChange={(v) => u.set({ sort: v })} options={[{ value: '', label: 'Most documented' }, { value: 'name', label: 'Name A–Z' }, { value: 'library', label: 'Library' }, { value: 'family', label: 'Family' }]} />
        <span className={s.filterMeta}>{list.data && `${list.data.meta.total_items.toLocaleString()} components`}</span>
      </div>
      <Panel>
        {list.error ? <ErrorState error={list.error} onRetry={() => list.refetch()} /> : (
          <DataTable
            caption="Components"
            loading={list.isFetching}
            rows={list.data?.data}
            rowKey={(r) => r.id}
            onRowClick={(r) => router.push(`/platform/components/${r.id}`)}
            sort={u.get('sort')}
            onSort={(k) => u.set({ sort: k })}
            columns={[
              { key: 'n', header: 'Component', sortKey: 'name', cell: (r) => <span className={s.cell}><strong>{r.name}</strong><small>{r.description ? r.description.slice(0, 110) + (r.description.length > 110 ? '…' : '') : ''}</small></span> },
              { key: 'lib', header: 'Library / system', sortKey: 'library', cell: (r) => r.library ?? <Missing /> },
              { key: 'fam', header: 'Family', sortKey: 'family', cell: (r) => (r.family ? <Tag>{r.family}</Tag> : <Missing label="—" />), hideBelow: 'md' },
              { key: 'lvl', header: 'Detail', cell: (r) => <Tag tone={r.detail_level === 'api' ? 'accent' : undefined}>{LEVEL[r.detail_level ?? ''] ?? r.detail_level}</Tag>, hideBelow: 'lg' },
              { key: 'p', header: 'Props', sortKey: 'props', cell: (r) => r.props_count || '—', align: 'right' },
              { key: 'k', header: 'Keys', cell: (r) => r.keyboard_count || '—', align: 'right', hideBelow: 'md' },
              { key: 'v', header: 'Verification', cell: (r) => <VerifyBadge status={r.verification_status} />, hideBelow: 'lg' },
            ]}
          />
        )}
        {list.data && <Pagination page={page} pageSize={25} total={list.data.meta.total_items} totalPages={list.data.meta.total_pages} onPage={(p) => u.set({ page: p }, { resetPage: false })} />}
      </Panel>
    </>
  )
}

export default function ComponentsPage() {
  return <Suspense><ComponentsInner /></Suspense>
}
