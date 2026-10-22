'use client'

import { Suspense, useState } from 'react'
import { X } from 'lucide-react'
import { useComponents } from '@/features/components/api'
import { useSystems } from '@/features/design-systems/api'
import { usePublicCompare } from '@/features/public/api'
import { useUrlState } from '@/hooks/useUrlState'
import { Button, EmptyState, ErrorState, PageHeader, Panel, SearchInput, Skeleton, Tabs, Tag, Toggle } from '@/components/ui'
import { ComparisonMatrix, type ComparisonResult } from '@/components/public/ComparisonMatrix'
import s from '@/components/platform/page.module.scss'

type Kind = 'systems' | 'components'
const DIMS: Record<Kind, string[]> = {
  systems: ['overview', 'frameworks', 'tokens', 'accessibility', 'styling', 'governance', 'components', 'sources', 'maintenance'],
  components: ['overview', 'api', 'state', 'keyboard', 'accessibility', 'structure', 'evidence'],
}

/** Read-only comparison computed by the backend from stored records. The selection lives in the URL (shareable); nothing is saved. */
function CompareInner() {
  const u = useUrlState()
  const kind = (u.get('kind') || 'systems') as Kind
  const ids = u.getAll('ids').flatMap((x) => x.split(',')).map(Number).filter(Boolean)
  const labels = u.getAll('labels').flatMap((x) => x.split('|'))
  const picked = ids.map((id, i) => ({ id, label: labels[i] || `#${id}` }))
  const dimsParam = u.getAll('dims').flatMap((x) => x.split(',')).filter(Boolean)
  const dims = dimsParam.length ? dimsParam : DIMS[kind]
  const [q, setQ] = useState('')
  const sys = useSystems({ q, page_size: 8 })
  const comps = useComponents({ q, has_props: true, page_size: 8 }, kind === 'components')
  const options = kind === 'systems' ? sys.data?.data.map((x) => ({ id: x.id, label: x.name, sub: x.organization ?? `${x.source_count} sources` }))
    : comps.data?.data.map((x) => ({ id: x.id, label: x.name, sub: `${x.library ?? ''} · ${x.props_count} props` }))
  const cmp = usePublicCompare(kind, ids, dims)
  const setPicked = (next: { id: number; label: string }[]) =>
    u.set({ ids: next.map((p) => p.id).join(',') || null, labels: next.map((p) => p.label.replace(/\|/g, ' ')).join('|') || null }, { resetPage: false })

  return (
    <>
      <PageHeader title="Compare" description="Pick 2–6 design systems or components. Every cell comes from stored records: documented, not documented (unknown), or not applicable. No scores or rankings." />
      <div className={s.grid21}>
        <Panel title="Choose what to compare">
          <div className={s.pad} style={{ display: 'grid', gap: 14 }}>
            <Tabs<Kind> value={kind} onChange={(k) => u.set({ kind: k, ids: null, labels: null, dims: null }, { resetPage: false })}
              tabs={[{ value: 'systems', label: 'Design systems' }, { value: 'components', label: 'Components' }]} />
            <SearchInput value={q} onChange={setQ} placeholder={kind === 'systems' ? 'Find design systems…' : 'Find components with documented APIs…'} />
            <ul className={s.list} style={{ border: '1px solid var(--line)', borderRadius: 10 }}>
              {options?.map((o) => {
                const on = picked.some((p) => p.id === o.id)
                return (
                  <li key={o.id} className={s.row} style={{ justifyContent: 'space-between' }}>
                    <span className={s.cell}><strong>{o.label}</strong><small>{o.sub}</small></span>
                    <Button size="sm" variant={on ? 'ghost' : 'secondary'} disabled={!on && picked.length >= 6}
                      onClick={() => setPicked(on ? picked.filter((p) => p.id !== o.id) : [...picked, { id: o.id, label: o.label }])}>{on ? 'Remove' : 'Add'}</Button>
                  </li>
                )
              })}
              {options?.length === 0 && <li className={s.muted}>No matches.</li>}
            </ul>
            <div>
              <p className={s.muted} style={{ fontSize: '0.8rem', marginBottom: 6 }}>Selected ({picked.length}/6, minimum 2)</p>
              <div className={s.row}>{picked.map((p) => (
                <Tag key={p.id}>{p.label} <button aria-label={`Remove ${p.label}`} onClick={() => setPicked(picked.filter((x) => x.id !== p.id))}
                  style={{ background: 'none', border: 0, color: 'inherit', cursor: 'pointer', display: 'grid' }}><X size={11} /></button></Tag>
              ))}</div>
            </div>
            <div>
              <p className={s.muted} style={{ fontSize: '0.8rem', marginBottom: 4 }}>Dimensions</p>
              <div className={s.row}>{DIMS[kind].map((d) => (
                <Toggle key={d} label={d} checked={dims.includes(d)}
                  onChange={(v) => u.set({ dims: (v ? [...dims, d] : dims.filter((x) => x !== d)).join(',') || null }, { resetPage: false })} />
              ))}</div>
            </div>
          </div>
        </Panel>
        <Panel title="How to read this">
          <div className={s.pad} style={{ display: 'grid', gap: 8, fontSize: '0.86rem' }}>
            <p>&quot;Not documented&quot; means the collected sources say nothing about it — not that the system lacks it.</p>
            <p className={s.muted}>Copy the page address to share this comparison.</p>
          </div>
        </Panel>
      </div>
      <div style={{ marginTop: 16 }}>
        {picked.length < 2 ? <EmptyState title="Select at least two items">Search above and add them to see their documented differences.</EmptyState>
          : cmp.error ? <ErrorState error={cmp.error} onRetry={() => cmp.refetch()} />
          : !cmp.data ? <Skeleton h={240} />
          : <ComparisonMatrix result={cmp.data.result as unknown as ComparisonResult} base={kind === 'systems' ? '/systems' : '/components'} />}
      </div>
    </>
  )
}

export default function ComparePage() {
  return <Suspense><CompareInner /></Suspense>
}
