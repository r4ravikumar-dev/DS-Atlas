'use client'

import { Suspense } from 'react'
import Link from 'next/link'
import { useSearch } from '@/features/search/api'
import { useUrlState } from '@/hooks/useUrlState'
import { EmptyState, ErrorState, PageHeader, Pagination, Panel, SearchInput, SkeletonRows, Tabs, Tag } from '@/components/ui'
import s from '@/components/platform/page.module.scss'

const TYPES = [
  { value: '', label: 'All' }, { value: 'system', label: 'Systems' }, { value: 'component', label: 'Components' }, { value: 'token', label: 'Tokens' },
  { value: 'guideline', label: 'Guidelines' }, { value: 'pattern', label: 'Patterns' }, { value: 'resource', label: 'Resources' }, { value: 'source', label: 'Sources' },
]

function SearchInner() {
  const u = useUrlState()
  const term = u.get('q')
  const type = u.get('type')
  const page = u.getNum('page', 1)
  const res = useSearch({ q: term, type: type || undefined, page, page_size: 20 })
  const facets = (res.data?.meta.facets ?? {}) as Record<string, number | string>
  const count = (t: string) => (t === '' ? undefined : t === 'guideline' ? Number(facets.guideline ?? 0) + Number(facets.specification ?? 0) : Number(facets[t] ?? 0) || undefined)
  return (
    <>
      <PageHeader title="Search" description="PostgreSQL full-text search with prefix matching across every persisted record type. Results link to their detail pages and evidence." />
      <div className={s.filters}><SearchInput value={term} onChange={(v) => u.set({ q: v })} placeholder="e.g. dialog, semantic tokens, keyboard, governance…" /></div>
      {term && <div style={{ marginBottom: 12 }}><Tabs value={type} onChange={(t) => u.set({ type: t })} tabs={TYPES.map((t) => ({ ...t, count: count(t.value) }))} /></div>}
      {!term ? <EmptyState title="Type to search the knowledge base" /> : res.error ? <ErrorState error={res.error} onRetry={() => res.refetch()} /> : !res.data ? <SkeletonRows rows={6} cols={2} /> : res.data.data.length === 0 ? (
        <EmptyState title={`No results for “${term}”`}>Try fewer or broader terms. Search covers titles, systems, organizations and summaries.</EmptyState>
      ) : (
        <Panel>
          {facets._match_mode === 'any' && <p className={`${s.pad} ${s.muted}`} style={{ fontSize: '0.82rem' }}>No record contains all terms — showing records matching any term, ranked by relevance.</p>}
          <ul className={s.list} style={{ opacity: res.isFetching ? 0.6 : 1 }}>
            {res.data.data.map((h) => (
              <li key={`${h.type}-${h.id}`}>
                <div className={s.row}><Tag tone="accent">{h.type}</Tag><Link href={h.url} style={{ fontWeight: 500 }}>{h.title}</Link>{h.subtitle && <span className={s.muted}>· {h.subtitle}</span>}{h.source_key && <span className={s.mono} style={{ marginLeft: 'auto' }}>{h.source_key}</span>}</div>
                {/* ts_headline wraps matches in <b>; render as text with emphasis by splitting, never as HTML */}
                {h.snippet && <p className={s.muted} style={{ fontSize: '0.84rem', marginTop: 4 }}>{h.snippet.split(/<\/?b>/).map((part, i) => (i % 2 ? <mark key={i} style={{ background: 'color-mix(in oklab, var(--accent) 35%, transparent)', color: 'inherit' }}>{part}</mark> : part))}</p>}
              </li>
            ))}
          </ul>
          <Pagination page={page} pageSize={20} total={res.data.meta.total_items} totalPages={res.data.meta.total_pages} onPage={(p) => u.set({ page: p }, { resetPage: false })} />
        </Panel>
      )}
    </>
  )
}

export default function SearchPage() {
  return <Suspense><SearchInner /></Suspense>
}
