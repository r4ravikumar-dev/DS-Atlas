'use client'

import { Suspense, useState } from 'react'
import Link from 'next/link'
import { can, useMe } from '@/features/auth/api'
import { useResolveReview, useReview } from '@/features/administration/api'
import { useUrlState } from '@/hooks/useUrlState'
import { Button, EmptyState, ErrorState, PageHeader, Pagination, Panel, Select, SkeletonRows, Tag } from '@/components/ui'
import s from '@/components/platform/page.module.scss'

const KINDS: Record<string, string> = { system_field_conflict: 'Conflicting field values', possible_duplicate_system: 'Possible duplicate systems', same_source_component_duplicate: 'Duplicate component (same source)' }

function ReviewInner() {
  const u = useUrlState()
  const { data: me } = useMe()
  const page = u.getNum('page', 1)
  const status = u.get('review_status', 'open')
  const list = useReview({ kind: u.get('kind'), review_status: status, page, page_size: 15 })
  const resolve = useResolveReview()
  const [notes, setNotes] = useState<Record<number, string>>({})
  return (
    <>
      <PageHeader title="Review queue" description="Deduplication never merges on names alone. Conflicts and uncertain duplicates are queued here; decisions are audited and preserved across rebuilds." />
      <div className={s.filters}>
        <Select label="Kind" value={u.get('kind')} onChange={(v) => u.set({ kind: v })} options={[{ value: '', label: 'All kinds' }, ...Object.entries(KINDS).map(([value, label]) => ({ value, label }))]} />
        <Select label="Status" value={status} onChange={(v) => u.set({ review_status: v })} options={['open', 'resolved', 'dismissed', 'all'].map((x) => ({ value: x, label: x }))} />
        <span className={s.filterMeta}>{list.data && `${list.data.meta.total_items} items`}</span>
      </div>
      {list.error ? <ErrorState error={list.error} /> : !list.data ? <SkeletonRows /> : list.data.data.length === 0 ? <EmptyState title="Nothing to review" /> : (
        <div className={s.stack}>
          {list.data.data.map((it) => {
            const d = it.details as Record<string, any> // eslint-disable-line @typescript-eslint/no-explicit-any
            return (
              <Panel key={it.id} title={<span className={s.row}><Tag tone="accent">{KINDS[it.kind] ?? it.kind}</Tag>{d.organization ?? d.entity ?? d.group}</span>} actions={<Tag>{it.review_status}</Tag>}>
                <div className={s.pad} style={{ display: 'grid', gap: 10 }}>
                  {d.reason && <p className={s.muted}>{d.reason}</p>}
                  {d.entities && <ul style={{ paddingLeft: 18 }}>{d.entities.map((e: any) => <li key={e.system_id}>{e.name} <span className={s.mono}>{e.site ?? 'no docs host'}</span></li>)}</ul>}
                  {d.details && <pre className={s.code}>{JSON.stringify(d.details, null, 2)}</pre>}
                  {d.records && <p className={s.mono}>{d.records.join(', ')}</p>}
                  {it.resolution_note && <p>Note: {it.resolution_note}</p>}
                  {can(me, 'researcher') && it.review_status === 'open' && (
                    <div className={s.row}>
                      <input aria-label="Resolution note" placeholder="Resolution note (optional)" value={notes[it.id] ?? ''} onChange={(e) => setNotes({ ...notes, [it.id]: e.target.value })}
                        style={{ flex: 1, minWidth: 200, height: 34, padding: '0 10px', borderRadius: 8, border: '1px solid var(--line-strong)', background: 'var(--surface)', color: 'var(--text)' }} maxLength={2000} />
                      <Button size="sm" onClick={() => resolve.mutate({ id: it.id, review_status: 'resolved', resolution_note: notes[it.id] })}>Mark resolved</Button>
                      <Button size="sm" variant="ghost" onClick={() => resolve.mutate({ id: it.id, review_status: 'dismissed', resolution_note: notes[it.id] })}>Dismiss</Button>
                    </div>
                  )}
                </div>
              </Panel>
            )
          })}
          <Pagination page={page} pageSize={15} total={list.data.meta.total_items} totalPages={list.data.meta.total_pages} onPage={(p) => u.set({ page: p }, { resetPage: false })} />
        </div>
      )}
      {list.data && <p className={s.muted} style={{ fontSize: '0.78rem', marginTop: 10 }}>Tip: open systems from the <Link href="/platform/systems">catalog</Link> to inspect conflicting claims in context.</p>}
    </>
  )
}

export default function ReviewPage() {
  return <Suspense><ReviewInner /></Suspense>
}
