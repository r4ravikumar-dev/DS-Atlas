import { Fragment } from 'react'
import Link from 'next/link'
import { Lightbulb } from 'lucide-react'
import { ExtLink, Panel, VerifyBadge } from '@/components/ui'
import s from '@/components/platform/page.module.scss'

export interface Cell { status: 'documented' | 'not_documented' | 'not_applicable'; value: unknown; evidence: string[] }
export interface ComparisonResult {
  columns: { id: number; name: string; library?: string; organization?: string; verification_status: string }[]
  dimensions: string[]
  rows: Record<string, Record<string, Cell[]>>
  interpretation: string[]
}

function renderValue(v: unknown): React.ReactNode {
  if (v === null || v === undefined) return null
  if (typeof v === 'string') return v.startsWith('http') ? <ExtLink href={v} /> : v
  if (typeof v === 'number' || typeof v === 'boolean') return String(v)
  if (Array.isArray(v)) return v.length > 8 ? <>{v.slice(0, 8).join(', ')} <span className={s.muted}>+{v.length - 8} more</span></> : v.join(', ')
  return Object.entries(v as Record<string, unknown>).slice(0, 10).map(([k, x]) => `${k}: ${typeof x === 'object' ? JSON.stringify(x) : x}`).join(' · ')
}

/** Documented differences only: an undocumented value is shown as "Not documented" (unknown), never as "not supported". */
export function ComparisonMatrix({ result: r, base }: { result: ComparisonResult; base: string }) {
  return (
    <>
      <div className={s.row} style={{ marginBottom: 12, fontSize: '0.8rem' }}>
        <span className={s.status_documented}>● documented</span><span className={s.status_not_documented}>● not documented (unknown)</span><span className={s.status_not_applicable}>● not applicable</span>
      </div>
      <Panel>
        <div className={s.matrix}>
          <table>
            <thead>
              <tr>
                <th scope="col">Dimension</th>
                {r.columns.map((col) => (
                  <th key={col.id} scope="col"><Link href={`${base}/${col.id}`}>{col.name}</Link><div className={s.muted} style={{ fontWeight: 400, fontSize: '0.76rem' }}>{col.library ?? col.organization}</div><VerifyBadge status={col.verification_status} /></th>
                ))}
              </tr>
            </thead>
            <tbody>
              {r.dimensions.map((dim) => (
                <Fragment key={dim}>
                  <tr className={s.dimRow}><th colSpan={r.columns.length + 1} scope="rowgroup">{dim}</th></tr>
                  {Object.entries(r.rows[dim] ?? {}).map(([label, cells]) => (
                    <tr key={label}>
                      <th scope="row">{label}</th>
                      {cells.map((cell, i) => (
                        <td key={i} className={s[`status_${cell.status}`]}>
                          {cell.status === 'documented' ? renderValue(cell.value) : cell.status === 'not_applicable' ? 'Not applicable' : 'Not documented'}
                          {cell.status === 'documented' && cell.evidence[0] && <div style={{ marginTop: 4, fontSize: '0.72rem' }}><a href={cell.evidence[0]} target="_blank" rel="noopener noreferrer" className={s.muted}>evidence ↗</a></div>}
                        </td>
                      ))}
                    </tr>
                  ))}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
      <Panel title={<span className={s.row}><Lightbulb size={15} /> Analytical interpretation (not source statements)</span>} id="interp">
        <ul className={s.list}>{r.interpretation.length ? r.interpretation.map((t, i) => <li key={i}>{t}</li>) : <li className={s.muted}>No notable cross-item observations.</li>}</ul>
      </Panel>
    </>
  )
}
