'use client'

import { useRouter } from 'next/navigation'
import { useGuidelineFacets, useGuidelines, type GKind } from '@/features/guidelines/api'
import { useUrlState } from '@/hooks/useUrlState'
import { ErrorState, FacetFilter, PageHeader, Pagination, Panel, SearchInput, Select, Tabs, Tag, VerifyBadge } from '@/components/ui'
import { DataTable } from '@/components/ui/DataTable'
import s from '@/components/platform/page.module.scss'

const CAT: Record<string, string> = { C01: 'Strategy', C02: 'Foundations', C03: 'Design tokens', C04: 'Component architecture', C05: 'Component catalog', C06: 'Patterns & workflows', C07: 'Accessibility', C08: 'Docs & governance', C09: 'Engineering & tooling', C10: 'Theming', C11: 'Cross-platform', C12: 'Research', C13: 'AI-ready knowledge' }

export function GuidelineList({ kind }: { kind: GKind }) {
  const u = useUrlState()
  const router = useRouter()
  const page = u.getNum('page', 1)
  const q = { q: u.get('q'), category: u.getAll('category'), kind: u.getAll('kind'), source: u.getAll('source'), verification: u.get('verification'), page, page_size: 25 }
  const list = useGuidelines(kind, q)
  const facets = useGuidelineFacets()
  return (
    <>
      <PageHeader title="Patterns & guidelines" description="Actionable findings: checklist requirements, specification sections, library documentation pages, design specs, governance write-ups and AI-readiness signals — each with source evidence." />
      <div style={{ marginBottom: 12 }}>
        <Tabs value={kind} onChange={(k) => router.push(`/platform/${k}`)} tabs={[{ value: 'guidelines' as GKind, label: 'Guidelines & specifications' }, { value: 'patterns' as GKind, label: 'Patterns' }]} />
      </div>
      <div className={s.filters}>
        <SearchInput value={u.get('q')} onChange={(v) => u.set({ q: v })} placeholder="Search guidance…" />
        <FacetFilter label="Category" facets={facets.data?.categories} selected={u.getAll('category')} onChange={(v) => u.set({ category: v })} format={(v) => `${v} ${CAT[v] ?? ''}`} />
        {kind === 'guidelines' && <FacetFilter label="Kind" facets={facets.data?.kinds} selected={u.getAll('kind')} onChange={(v) => u.set({ kind: v })} format={(v) => v.replace(/_/g, ' ')} />}
        <FacetFilter label="Source" facets={facets.data?.sources} selected={u.getAll('source')} onChange={(v) => u.set({ source: v })} />
        {kind === 'guidelines' && <Select label="Verification" value={u.get('verification')} onChange={(v) => u.set({ verification: v })} options={[{ value: '', label: 'Any verification' }, { value: 'verified', label: 'Verified' }, { value: 'partially_verified', label: 'Partially verified' }, { value: 'unverified', label: 'Unverified' }]} />}
        <span className={s.filterMeta}>{list.data && `${list.data.meta.total_items.toLocaleString()} items`}</span>
      </div>
      <Panel>
        {list.error ? <ErrorState error={list.error} onRetry={() => list.refetch()} /> : (
          <DataTable caption={kind} loading={list.isFetching} rows={list.data?.data} rowKey={(r) => r.id} onRowClick={(r) => router.push(`/platform/${kind}/${r.id}`)}
            columns={[
              { key: 't', header: 'Title', cell: (r) => <span className={s.cell}><strong>{r.title}</strong><small>{r.summary ? r.summary.slice(0, 140) + (r.summary.length > 140 ? '…' : '') : ''}</small></span> },
              { key: 'c', header: 'Category', cell: (r) => <Tag>{r.category} {CAT[r.category]}</Tag>, hideBelow: 'md' },
              { key: 'k', header: 'Kind', cell: (r) => <span className={s.muted}>{(r.kind ?? r.record_type).replace(/_/g, ' ')}</span>, hideBelow: 'lg' },
              { key: 's', header: 'Source', cell: (r) => <span className={s.mono}>{r.source_key}</span>, hideBelow: 'md' },
              { key: 'v', header: 'Verification', cell: (r) => <VerifyBadge status={r.verification_status} /> },
            ]} />
        )}
        {list.data && <Pagination page={page} pageSize={25} total={list.data.meta.total_items} totalPages={list.data.meta.total_pages} onPage={(p) => u.set({ page: p }, { resetPage: false })} />}
      </Panel>
    </>
  )
}
