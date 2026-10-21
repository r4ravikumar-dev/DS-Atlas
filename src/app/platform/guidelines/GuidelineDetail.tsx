'use client'

import { useParams } from 'next/navigation'
import { Info } from 'lucide-react'
import { useGuideline, type GKind } from '@/features/guidelines/api'
import { ErrorState, ExtLink, fmtDate, KV, PageHeader, Panel, Skeleton, Tag, VerifyBadge } from '@/components/ui'
import s from '@/components/platform/page.module.scss'

const LABEL: Record<string, string> = { requirement: 'Requirement', source_wording: 'Source wording', section_description: 'Section context', rationale: 'Rationale', verification_method: 'Verification method',
  priority: 'Priority', text: 'Text', evaluation_guidance: 'Evaluation guidance', known_for: 'Known for', watch_outs: 'Watch-outs', note: 'Note', status: 'Status', method: 'Method', source: 'Evidence URL', documentation_url: 'Documentation' }

export function GuidelineDetailView({ kind }: { kind: GKind }) {
  const id = Number(useParams<{ id: string }>().id)
  const g = useGuideline(kind, id)
  if (g.error) return <ErrorState error={g.error} onRetry={() => g.refetch()} />
  const d = g.data
  const content = (d?.content ?? {}) as Record<string, unknown>
  const shown = Object.entries(content).filter(([k, v]) => v !== null && v !== '' && !(Array.isArray(v) && v.length === 0) && !['kind', 'checklist_id', 'order', 'section_id', 'section_resources', 'outline', 'heading_path'].includes(k))
  return (
    <>
      <PageHeader crumbs={[{ href: `/platform/${kind}`, label: kind === 'patterns' ? 'Patterns' : 'Guidelines' }]} title={d ? d.title : <Skeleton w={320} h={30} />}
        description={d && <span className={s.row}><VerifyBadge status={d.verification_status} /><Tag>{d.category} {d.category_name}</Tag>{d.kind && <Tag>{d.kind.replace(/_/g, ' ')}</Tag>}<span className={s.mono}>{d.source_key}</span><span className={s.muted}>confidence: {d.confidence}</span></span>} />
      {d && (
        <div className={s.grid21}>
          <Panel title="Guidance">
            <div className={s.pad}>
              {d.summary && <p style={{ marginBottom: 14 }}>{d.summary}</p>}
              <KV items={shown.map(([k, v]) => [LABEL[k] ?? k.replace(/_/g, ' '), typeof v === 'string' ? (v.startsWith('http') ? <ExtLink href={v} /> : v) : <pre className={s.code}>{JSON.stringify(v, null, 2)}</pre>])} />
              {d.priority === null && <p className={s.muted} style={{ fontSize: '0.8rem', marginTop: 10 }}>Priority is not stated by the source and is left empty.</p>}
            </div>
          </Panel>
          <div className={s.stack}>
            <div className={s.notice}><Info size={16} aria-hidden /><span>Shown as extracted from the source (original wording or a short faithful paraphrase). Research-derived recommendations live in Reports.</span></div>
            <Panel title="Evidence">
              <ul className={s.list}>
                {d.evidence.map((e) => (
                  <li key={e.id}>
                    <ExtLink href={e.url} />
                    <div className={s.muted} style={{ fontSize: '0.78rem', marginTop: 4 }}>{e.source_section && <>Section: {e.source_section} · </>}{e.source_version && <>Version {e.source_version.slice(0, 12)} · </>}captured {fmtDate(e.captured_at)}</div>
                    {e.excerpt && <blockquote style={{ margin: '6px 0 0', paddingLeft: 10, borderLeft: '2px solid var(--line-strong)', color: 'var(--muted)', fontSize: '0.82rem' }}>{e.excerpt}</blockquote>}
                  </li>
                ))}
              </ul>
            </Panel>
          </div>
        </div>
      )}
    </>
  )
}
