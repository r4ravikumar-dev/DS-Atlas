'use client'

import { Fragment, useState } from 'react'
import Link from 'next/link'
import { useParams, useRouter } from 'next/navigation'
import { Lightbulb, RefreshCw, Trash2 } from 'lucide-react'
import { can, useMe } from '@/features/auth/api'
import { useComparison, useDeleteComparison, useRegenerate } from '@/features/comparisons/api'
import { Button, ConfirmDialog, ErrorState, ExtLink, fmtDate, PageHeader, Panel, Skeleton, VerifyBadge } from '@/components/ui'
import s from '@/components/platform/page.module.scss'

interface Cell { status: 'documented' | 'not_documented' | 'not_applicable'; value: unknown; evidence: string[] }
interface Result { columns: { id: number; name: string; library?: string; organization?: string; verification_status: string }[]; dimensions: string[]; rows: Record<string, Record<string, Cell[]>>; interpretation: string[] }

function renderValue(v: unknown): React.ReactNode {
  if (v === null || v === undefined) return null
  if (typeof v === 'string') return v.startsWith('http') ? <ExtLink href={v} /> : v
  if (typeof v === 'number' || typeof v === 'boolean') return String(v)
  if (Array.isArray(v)) return v.length > 8 ? <>{v.slice(0, 8).join(', ')} <span className={s.muted}>+{v.length - 8} more</span></> : v.join(', ')
  return Object.entries(v as Record<string, unknown>).slice(0, 10).map(([k, x]) => `${k}: ${typeof x === 'object' ? JSON.stringify(x) : x}`).join(' · ')
}

export default function ComparisonPage() {
  const id = useParams<{ id: string }>().id
  const router = useRouter()
  const { data: me } = useMe()
  const c = useComparison(id)
  const regen = useRegenerate(id)
  const del = useDeleteComparison()
  const [confirm, setConfirm] = useState(false)
  if (c.error) return <ErrorState error={c.error} onRetry={() => c.refetch()} />
  const d = c.data
  const r = d?.result as unknown as Result | undefined
  const base = d?.kind === 'systems' ? '/platform/systems' : '/platform/components'
  return (
    <>
      <PageHeader crumbs={[{ href: '/platform/compare', label: 'Compare' }]} title={d ? d.name : <Skeleton w={300} h={30} />}
        description={d && `${d.kind} · generated ${fmtDate(d.generated_at)} from current records`}
        actions={d && can(me, 'researcher') && (<>
          <Button icon={<RefreshCw size={14} />} loading={regen.isPending} onClick={() => regen.mutate()}>Regenerate</Button>
          <Button variant="ghost" icon={<Trash2 size={14} />} onClick={() => setConfirm(true)}>Delete</Button>
        </>)} />
      {r && (
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
          <Panel title={<span className={s.row}><Lightbulb size={15} /> Analytical interpretation (not source statements)</span>} className="" id="interp">
            <ul className={s.list}>{r.interpretation.length ? r.interpretation.map((t, i) => <li key={i}>{t}</li>) : <li className={s.muted}>No notable cross-item observations.</li>}</ul>
          </Panel>
        </>
      )}
      <ConfirmDialog open={confirm} danger title="Delete this comparison?" body="The saved configuration and generated result will be removed. Source records are not affected." confirmLabel="Delete" loading={del.isPending}
        onCancel={() => setConfirm(false)} onConfirm={() => del.mutate(id, { onSuccess: () => router.push('/platform/compare') })} />
    </>
  )
}
