'use client'

import { Fragment, useState } from 'react'
import Link from 'next/link'
import { AnimatePresence, motion } from 'motion/react'
import { Lightbulb } from 'lucide-react'
import { duration, ease } from '@/lib/motion/tokens'
import { cn } from '@/lib/cn'
import { ExternalLink } from '../kit/external-link'

export type CellStatus = 'documented' | 'partially_documented' | 'not_documented' | 'not_inspected' | 'not_applicable'
export interface Cell { status: CellStatus; value: unknown; evidence: string[] }
export interface ComparisonResult {
  columns: { id: number; name: string; library?: string; organization?: string; verification_status?: string }[]
  dimensions: string[]
  rows: Record<string, Record<string, Cell[]>>
  interpretation: string[]
  shared_props?: string[]
  prop_matrix?: Record<string, string[]>
}

export const STATUS: Record<CellStatus, { label: string; mark: string; cls: string }> = {
  documented: { label: 'Documented', mark: '●', cls: 'text-success' },
  partially_documented: { label: 'Partially documented', mark: '◐', cls: 'text-accent-text' },
  not_documented: { label: 'Not documented (unknown — not "unsupported")', mark: '○', cls: 'text-muted' },
  // the collected sources say nothing about it — presented the same way as "not documented"
  not_inspected: { label: 'Not documented (unknown — not "unsupported")', mark: '○', cls: 'text-muted' },
  not_applicable: { label: 'Not applicable', mark: '—', cls: 'text-faint' },
}

const DIM_LABEL: Record<string, string> = {
  overview: 'Overview', frameworks: 'Framework support', tokens: 'Token structure', accessibility: 'Accessibility', styling: 'Styling & theming',
  governance: 'Governance', components: 'Component composition', sources: 'Documentation coverage', maintenance: 'Maintenance',
  api: 'Component API', state: 'State model', keyboard: 'Keyboard', structure: 'Structure', evidence: 'Evidence',
}

function renderValue(v: unknown): React.ReactNode {
  if (v === null || v === undefined) return null
  if (typeof v === 'string') return /^https?:\/\//.test(v) ? <ExternalLink href={v} className="break-all" /> : /^\d{4}-\d\d-\d\dT/.test(v) ? new Date(v).toLocaleDateString('en', { dateStyle: 'medium', timeZone: 'UTC' }) : v
  if (typeof v === 'number' || typeof v === 'boolean') return v === true ? 'Yes' : String(v)
  if (Array.isArray(v)) return (
    <ul className="flex flex-wrap gap-1">
      {v.slice(0, 10).map((x, i) => <li key={i} className="rounded-xs bg-surface-2 px-1.5 py-0.5 font-mono text-[0.7rem]">{String(x)}</li>)}
      {v.length > 10 && <li className="text-[0.7rem] text-muted">+{v.length - 10} more</li>}
    </ul>
  )
  return (
    <ul className="flex flex-col gap-0.5 font-mono text-[0.72rem]">
      {Object.entries(v as Record<string, unknown>).slice(0, 10).map(([k, x]) => <li key={k}><span className="text-muted">{k}</span> {typeof x === 'object' ? JSON.stringify(x) : String(x)}</li>)}
    </ul>
  )
}

const same = (cells: Cell[]) => cells.every((c) => c.status === cells[0].status && JSON.stringify(c.value) === JSON.stringify(cells[0].value))

/**
 * Side-by-side matrix. Rows whose values differ are marked; "Only differences" hides the rest.
 * An undocumented value is never presented as missing support. On narrow screens each row stacks per item.
 */
export function ComparisonMatrix({ result: r, base }: { result: ComparisonResult; base: string }) {
  const [onlyDiff, setOnlyDiff] = useState(false)
  const n = r.columns.length
  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <ul className="flex flex-wrap gap-x-5 gap-y-1.5 text-[0.75rem]" aria-label="Legend">
          {(['documented', 'partially_documented', 'not_documented', 'not_applicable'] as CellStatus[]).map((k) => <li key={k} className={cn('flex items-center gap-1.5', STATUS[k].cls)}><span aria-hidden>{STATUS[k].mark}</span><span className="text-text-2">{STATUS[k].label}</span></li>)}
        </ul>
        <label className="flex cursor-pointer items-center gap-2 text-meta text-text-2">
          <input type="checkbox" checked={onlyDiff} onChange={(e) => setOnlyDiff(e.target.checked)} className="focus-ring size-4 accent-[var(--accent)]" />
          Only show differences
        </label>
      </div>

      <div className="focus-ring overflow-x-auto rounded-sm border border-line" tabIndex={0} role="region" aria-label="Comparison table (scrolls horizontally)">
        <table className="w-full min-w-[40rem] border-collapse text-left text-meta">
          <caption className="sr-only">Comparison of {r.columns.map((c) => c.name).join(', ')}</caption>
          <thead className="sticky top-0 z-10 bg-bg">
            <tr className="border-b border-line-strong">
              <th scope="col" className="w-48 px-4 py-4 align-bottom font-normal text-muted">Attribute</th>
              {r.columns.map((col) => (
                <th key={col.id} scope="col" className="px-4 py-4 align-bottom font-normal">
                  <Link href={`${base}/${col.id}`} className="focus-ring block text-card font-medium text-text hover:text-accent-text">{col.name}</Link>
                  <span className="block text-meta text-muted">{col.library ?? col.organization ?? '—'}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {r.dimensions.map((dim) => {
              const entries = Object.entries(r.rows[dim] ?? {}).filter(([, cells]) => !onlyDiff || !same(cells))
              if (entries.length === 0) return null
              return (
                <Fragment key={dim}>
                  <tr><th colSpan={n + 1} scope="rowgroup" className="border-b border-line bg-bg-2 px-4 pt-6 pb-2 text-left font-mono text-caption font-normal tracking-[0.08em] text-muted uppercase">{DIM_LABEL[dim] ?? dim}</th></tr>
                  <AnimatePresence initial={false}>
                    {entries.map(([label, cells]) => {
                      const differs = !same(cells)
                      return (
                        <motion.tr key={label} layout initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: duration.fast, ease: ease.out }}
                          className={cn('border-b border-line align-top', differs && 'bg-accent-soft/40')}>
                          <th scope="row" className="px-4 py-3 font-normal text-text-2">
                            {label}{differs && <span className="ml-2 font-mono text-[0.62rem] tracking-wide text-accent-text uppercase">differs</span>}
                          </th>
                          {cells.map((c, i) => (
                            <td key={i} className="px-4 py-3">
                              <span className="flex items-start gap-2">
                                <span className={cn('mt-0.5 shrink-0', STATUS[c.status]?.cls)} aria-hidden>{STATUS[c.status]?.mark}</span>
                                <span className="min-w-0">
                                  {c.status === 'documented' ? <span className="text-text">{renderValue(c.value)}</span> : <span className="text-muted italic">{STATUS[c.status]?.label.replace(/ \(.*/, '')}</span>}
                                  <span className="sr-only"> ({STATUS[c.status]?.label})</span>
                                  {c.status === 'documented' && c.evidence[0] && <ExternalLink href={c.evidence[0]} className="mt-1 block w-fit text-[0.7rem] text-muted">evidence</ExternalLink>}
                                </span>
                              </span>
                            </td>
                          ))}
                        </motion.tr>
                      )
                    })}
                  </AnimatePresence>
                </Fragment>
              )
            })}
          </tbody>
        </table>
      </div>

      {r.prop_matrix && <PropOverlap columns={r.columns} matrix={r.prop_matrix} shared={r.shared_props ?? []} />}

      <section aria-labelledby="interp" className="rounded-sm border border-line p-6">
        <h2 id="interp" className="mb-3 flex items-center gap-2 text-card font-medium"><Lightbulb className="size-4 text-accent-text" aria-hidden />Interpretation <span className="text-meta font-normal text-muted">— analysis, not source statements</span></h2>
        <ul className="flex list-disc flex-col gap-2 pl-5 text-[0.92rem] text-text-2">
          {r.interpretation.length ? r.interpretation.map((t, i) => <li key={i}>{t}</li>) : <li className="list-none text-muted">No notable cross-item observations.</li>}
        </ul>
      </section>
    </div>
  )
}

/** API overlap for component comparisons: props every item documents, and the ones unique to each. */
function PropOverlap({ columns, matrix, shared }: { columns: ComparisonResult['columns']; matrix: Record<string, string[]>; shared: string[] }) {
  const sharedSet = new Set(shared)
  return (
    <section aria-labelledby="overlap" className="flex flex-col gap-4">
      <h2 id="overlap" className="text-card font-medium">API overlap</h2>
      <p className="text-meta text-text-2">{shared.length ? <>Props documented by every compared component: <span className="font-mono text-text">{shared.slice(0, 24).join(', ')}</span></> : 'No prop name is documented by all compared components.'}</p>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {columns.map((col) => {
          const own = (matrix[String(col.id)] ?? []).filter((p) => !sharedSet.has(p))
          return (
            <div key={col.id} className="rounded-sm border border-line p-4">
              <p className="mb-2 text-meta"><span className="text-text">{col.name}</span> <span className="text-muted">· {own.length} not shared</span></p>
              <ul className="flex flex-wrap gap-1">{own.slice(0, 40).map((p) => <li key={p} className="rounded-xs bg-surface-2 px-1.5 py-0.5 font-mono text-[0.68rem] text-text-2">{p}</li>)}</ul>
            </div>
          )
        })}
      </div>
    </section>
  )
}
