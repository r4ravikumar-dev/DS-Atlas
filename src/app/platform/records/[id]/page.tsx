'use client'

import Link from 'next/link'
import { useParams } from 'next/navigation'
import { useRecord } from '@/features/guidelines/api'
import { ErrorState, ExtLink, fmtDate, KV, PageHeader, Panel, Skeleton, Tag, VerifyBadge } from '@/components/ui'
import s from '@/components/platform/page.module.scss'

export default function RecordPage() {
  const id = Number(useParams<{ id: string }>().id)
  const r = useRecord(id)
  if (r.error) return <ErrorState error={r.error} onRetry={() => r.refetch()} />
  const d = r.data
  return (
    <>
      <PageHeader title={d ? d.title : <Skeleton w={320} h={30} />}
        description={d && <span className={s.row}><Tag>{d.record_type}</Tag><VerifyBadge status={d.verification_status} /><span className={s.mono}>{d.record_key}</span>{d.is_stale && <Tag>stale</Tag>}</span>} />
      {d && (
        <div className={s.grid21}>
          <Panel title="Record">
            <div className={s.pad}>
              {d.summary && <p style={{ marginBottom: 12 }}>{d.summary}</p>}
              <KV items={[
                ['Source', `${d.source_key} · ${d.source_name}`], ['Evidence URL', <ExtLink key="e" href={d.source_url} />], ['Design system', d.system_id ? <Link href={`/platform/systems/${d.system_id}`}>{d.design_system_name ?? 'Open system'}</Link> : d.design_system_name],
                ['Organization', d.organization], ['Category', d.primary_category], ['Confidence', d.confidence], ['Source version', d.source_version], ['Last verified', fmtDate(d.last_verified_at)],
              ]} />
            </div>
          </Panel>
          <div className={s.stack}>
            <Panel title="Normalized content (source-native)"><div className={s.pad}><pre className={s.code} style={{ maxHeight: 420 }}>{JSON.stringify(d.content, null, 2)}</pre></div></Panel>
            {d.notes.length > 0 && <Panel title="Notes"><ul className={s.list}>{d.notes.map((n, i) => <li key={i}>{n}</li>)}</ul></Panel>}
            <Panel title="Evidence">
              <ul className={s.list}>{d.evidence.map((e) => <li key={e.id}><ExtLink href={e.url} />{e.raw_document_id && <> · <a className={s.mono} href={`/api/v1/documents/${e.raw_document_id}/content`}>snapshot #{e.raw_document_id}</a></>}{e.excerpt && <p className={s.muted} style={{ fontSize: '0.8rem', marginTop: 4 }}>{e.excerpt}</p>}</li>)}</ul>
            </Panel>
          </div>
        </div>
      )}
    </>
  )
}
