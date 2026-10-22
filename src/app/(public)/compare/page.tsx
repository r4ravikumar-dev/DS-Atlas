'use client'

import { Suspense, useState } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { Plus, Search, X } from 'lucide-react'
import { useComponents } from '@/features/components/api'
import { useSystems } from '@/features/design-systems/api'
import { usePublicCompare } from '@/features/public/api'
import { useDebounced } from '@/hooks/useDebounced'
import { useUrlState } from '@/hooks/useUrlState'
import { spring } from '@/lib/motion/tokens'
import { cn } from '@/lib/cn'
import { ComparisonMatrix, type ComparisonResult } from '@/components/comparison/ComparisonMatrix'
import { EmptyState, ErrorNotice } from '@/components/kit/states'
import { Skeleton } from '@/components/kit/skeleton'

type Kind = 'systems' | 'components'
const DIMS: Record<Kind, { value: string; label: string }[]> = {
  systems: [
    { value: 'overview', label: 'Overview' }, { value: 'frameworks', label: 'Frameworks' }, { value: 'components', label: 'Components' }, { value: 'styling', label: 'Styling' },
    { value: 'tokens', label: 'Tokens' }, { value: 'accessibility', label: 'Accessibility' }, { value: 'sources', label: 'Documentation coverage' }, { value: 'governance', label: 'Governance' }, { value: 'maintenance', label: 'Maintenance' },
  ],
  components: [
    { value: 'overview', label: 'Overview' }, { value: 'api', label: 'API' }, { value: 'state', label: 'State' }, { value: 'keyboard', label: 'Keyboard' },
    { value: 'accessibility', label: 'Accessibility' }, { value: 'structure', label: 'Structure' }, { value: 'evidence', label: 'Evidence' },
  ],
}

/** Comparison workspace. The selection lives in the URL (shareable); the backend computes the matrix from stored records; nothing is saved. */
function CompareInner() {
  const u = useUrlState()
  const kind = (u.get('kind') || 'systems') as Kind
  const ids = u.getAll('ids').flatMap((x) => x.split(',')).map(Number).filter(Boolean).slice(0, 6)
  const labels = u.getAll('labels').flatMap((x) => x.split('|'))
  const picked = ids.map((id, i) => ({ id, label: labels[i] || `#${id}` }))
  const dimsParam = u.getAll('dims').flatMap((x) => x.split(',')).filter(Boolean)
  const dims = dimsParam.length ? dimsParam : DIMS[kind].map((d) => d.value)
  const [q, setQ] = useState('')
  const dq = useDebounced(q, 250)
  const sys = useSystems({ q: dq, page_size: 8 })
  const comps = useComponents({ q: dq, has_props: true, page_size: 8 }, kind === 'components')
  const options = kind === 'systems'
    ? sys.data?.data.map((x) => ({ id: x.id, label: x.name, sub: x.organization ?? `${x.source_count} sources` }))
    : comps.data?.data.map((x) => ({ id: x.id, label: `${x.name} (${x.library ?? '—'})`, sub: `${x.family ?? 'Unclassified'} · ${x.props_count} props` }))
  const cmp = usePublicCompare(kind, ids, dims)
  const setPicked = (next: { id: number; label: string }[]) =>
    u.set({ ids: next.map((p) => p.id).join(',') || null, labels: next.map((p) => p.label.replace(/\|/g, ' ')).join('|') || null }, { resetPage: false })

  return (
    <>
      <header className="border-b border-line">
        <div className="container-page pt-14 pb-10 md:pt-20">
          <p className="eyebrow mb-4">Workspace</p>
          <h1 className="text-title font-medium">Compare <span className="font-serif font-normal text-muted italic">what the sources say.</span></h1>
          <p className="measure mt-5 text-lg text-text-2">Pick two to six design systems or components. Every cell comes from stored records: documented, not documented (unknown, not “unsupported”), or not applicable. No scores, no rankings. Copy the address to share the comparison.</p>
        </div>
      </header>

      <div className="container-page grid gap-8 pt-8 lg:grid-cols-[22rem_minmax(0,1fr)]">
        <aside className="flex flex-col gap-6 lg:sticky lg:top-[calc(var(--header-h)+1.5rem)] lg:self-start" aria-label="Selection">
          <div role="radiogroup" aria-label="What to compare" className="grid grid-cols-2 rounded-sm border border-line-strong p-1">
            {(['systems', 'components'] as Kind[]).map((k) => (
              <button key={k} type="button" role="radio" aria-checked={kind === k} onClick={() => kind !== k && u.set({ kind: k, ids: null, labels: null, dims: null }, { resetPage: false })}
                className={cn('focus-ring relative h-9 rounded-xs text-meta transition-colors', kind === k ? 'text-accent-ink' : 'text-muted hover:text-text')}>
                {kind === k && <motion.span layoutId="cmp-kind" className="absolute inset-0 rounded-xs bg-accent" transition={spring.snappy} />}
                <span className="relative">{k === 'systems' ? 'Design systems' : 'Components'}</span>
              </button>
            ))}
          </div>

          <div>
            <p className="eyebrow mb-2">Selected ({picked.length}/6 · at least 2)</p>
            <ul className="flex flex-wrap gap-1.5" aria-live="polite">
              <AnimatePresence initial={false}>
                {picked.map((p) => (
                  <motion.li key={p.id} layout initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.9 }} transition={spring.snappy}
                    className="inline-flex h-8 items-center gap-1.5 rounded-xs border border-line-strong bg-surface-2 pr-1 pl-2.5 text-meta">
                    {p.label}
                    <button type="button" aria-label={`Remove ${p.label}`} onClick={() => setPicked(picked.filter((x) => x.id !== p.id))} className="focus-ring grid size-6 place-items-center rounded-xs text-muted hover:text-text"><X className="size-3.5" /></button>
                  </motion.li>
                ))}
              </AnimatePresence>
              {picked.length === 0 && <li className="text-meta text-faint">Nothing selected yet.</li>}
            </ul>
          </div>

          <div className="flex flex-col gap-2">
            <label htmlFor="cmp-q" className="eyebrow">Add {kind === 'systems' ? 'a design system' : 'a component'}</label>
            <div className="relative">
              <Search className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted" aria-hidden />
              <input id="cmp-q" type="search" value={q} onChange={(e) => setQ(e.target.value)} maxLength={200} autoComplete="off"
                placeholder={kind === 'systems' ? 'Find design systems…' : 'Find components with documented APIs…'}
                className="focus-ring h-10 w-full rounded-sm border border-line-strong bg-surface pr-3 pl-9 text-[0.9rem] placeholder:text-faint focus:border-accent focus:outline-none" />
            </div>
            <ul className="flex flex-col divide-y divide-line rounded-sm border border-line">
              {options?.map((o) => {
                const on = picked.some((p) => p.id === o.id)
                return (
                  <li key={o.id} className="flex items-center justify-between gap-3 px-3 py-2">
                    <span className="min-w-0"><span className="block truncate text-[0.9rem]">{o.label}</span><span className="block truncate text-[0.72rem] text-muted">{o.sub}</span></span>
                    <button type="button" disabled={!on && picked.length >= 6} aria-pressed={on}
                      onClick={() => setPicked(on ? picked.filter((p) => p.id !== o.id) : [...picked, { id: o.id, label: o.label }])}
                      className={cn('focus-ring inline-flex h-8 shrink-0 items-center gap-1 rounded-xs px-2.5 text-meta transition-colors disabled:opacity-40', on ? 'bg-accent text-accent-ink' : 'border border-line-strong hover:bg-surface-2')}>
                      {on ? <><X className="size-3.5" aria-hidden />Remove</> : <><Plus className="size-3.5" aria-hidden />Add</>}
                    </button>
                  </li>
                )
              })}
              {!options && <li className="p-3"><Skeleton className="h-24" /></li>}
              {options?.length === 0 && <li className="px-3 py-4 text-meta text-muted">No matches.</li>}
            </ul>
          </div>

          <fieldset>
            <legend className="eyebrow mb-2">Dimensions</legend>
            <div className="flex flex-wrap gap-1.5">
              {DIMS[kind].map((d) => {
                const on = dims.includes(d.value)
                return (
                  <button key={d.value} type="button" aria-pressed={on}
                    onClick={() => u.set({ dims: (on ? dims.filter((x) => x !== d.value) : [...dims, d.value]).join(',') || null }, { resetPage: false })}
                    className={cn('focus-ring h-8 rounded-xs border px-2.5 text-meta transition-colors', on ? 'border-text/40 bg-surface-2 text-text' : 'border-dashed border-line text-muted hover:text-text')}>
                    {d.label}
                  </button>
                )
              })}
            </div>
          </fieldset>
        </aside>

        <section aria-label="Comparison" className="min-w-0">
          {picked.length < 2 ? (
            <EmptyState title="Select at least two items" backToSite={false}>Search on the left and add them to see their documented differences side by side.</EmptyState>
          ) : cmp.error ? (
            <ErrorNotice title="The comparison could not be computed" message={cmp.error.message} onRetry={() => cmp.refetch()} />
          ) : !cmp.data ? (
            <div className="flex flex-col gap-2" aria-busy><Skeleton className="h-12" /><Skeleton className="h-64" /></div>
          ) : (
            <ComparisonMatrix result={cmp.data.result as unknown as ComparisonResult} base={kind === 'systems' ? '/systems' : '/components'} />
          )}
        </section>
      </div>
    </>
  )
}

export default function ComparePage() {
  return <Suspense><CompareInner /></Suspense>
}
