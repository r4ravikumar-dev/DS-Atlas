'use client'

import { useMemo, useState } from 'react'
import type { Prop } from '@/lib/api/types'
import { NotDocumented } from '../kit/states'

const STEP = 60

/** Filterable props table for one component (client-side: the full documented list is already on the page). */
export function PropsExplorer({ props }: { props: Prop[] }) {
  const [q, setQ] = useState('')
  const [part, setPart] = useState('')
  const [limit, setLimit] = useState(STEP)
  const parts = useMemo(() => [...new Set(props.map((p) => p.subcomponent).filter(Boolean))] as string[], [props])
  const shown = useMemo(() => {
    const n = q.trim().toLowerCase()
    return props.filter((p) => (!part || p.subcomponent === part) && (!n || `${p.name} ${p.type ?? ''} ${p.description ?? ''}`.toLowerCase().includes(n)))
  }, [props, q, part])

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-2">
        <label className="sr-only" htmlFor="prop-q">Filter props</label>
        <input id="prop-q" type="search" value={q} onChange={(e) => (setQ(e.target.value), setLimit(STEP))} placeholder="Filter props by name, type or description"
          className="focus-ring h-10 min-w-0 flex-1 basis-64 rounded-sm border border-line-strong bg-surface px-3 text-[0.9rem] placeholder:text-faint focus:border-accent focus:outline-none" />
        {parts.length > 1 && (
          <label className="flex h-10 items-center gap-2 rounded-sm border border-line-strong bg-surface pr-1 pl-3 text-meta text-muted">
            Part
            <select value={part} onChange={(e) => (setPart(e.target.value), setLimit(STEP))} className="focus-ring h-8 border-0 bg-transparent text-text outline-none">
              <option value="">All ({parts.length})</option>
              {parts.map((x) => <option key={x} value={x}>{x}</option>)}
            </select>
          </label>
        )}
        <span className="font-mono text-meta text-muted" aria-live="polite">{shown.length.toLocaleString()} props</span>
      </div>
      <div className="focus-ring overflow-x-auto rounded-sm border border-line" tabIndex={0} role="region" aria-label="Props table (scrolls horizontally)">
        <table className="w-full min-w-[44rem] text-left text-meta">
          <thead className="border-b border-line bg-surface/60">
            <tr>{['Prop', 'Type', 'Default', 'Description'].map((h) => <th key={h} scope="col" className="px-3 py-2.5 font-normal text-muted">{h}</th>)}</tr>
          </thead>
          <tbody className="divide-y divide-line">
            {shown.slice(0, limit).map((p) => (
              <tr key={`${p.subcomponent}-${p.name}`} className="align-top hover:bg-surface/50">
                <td className="px-3 py-2.5 font-mono text-text">
                  {p.name}{p.required && !/^(false|no)$/i.test(p.required) ? <span className="text-danger" title="required"> *</span> : null}
                  {parts.length > 1 && <span className="block text-[0.68rem] text-faint">{p.subcomponent}</span>}
                </td>
                <td className="max-w-[18rem] px-3 py-2.5 font-mono break-words text-violet">{p.type ?? '—'}</td>
                <td className="px-3 py-2.5 font-mono text-text-2">{p.default_value ?? '—'}</td>
                <td className="px-3 py-2.5 text-text-2">{p.description ?? <NotDocumented />}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {shown.length > limit && (
        <button type="button" onClick={() => setLimit(limit + STEP * 2)} className="focus-ring w-fit text-meta text-accent-text underline decoration-accent/40 underline-offset-4 hover:decoration-accent">
          Show more ({(shown.length - limit).toLocaleString()} remaining)
        </button>
      )}
    </div>
  )
}
