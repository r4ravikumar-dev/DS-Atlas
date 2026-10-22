'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useParams, useRouter } from 'next/navigation'
import { RotateCcw, Square } from 'lucide-react'
import { isAdmin, useMe } from '@/features/auth/api'
import { isActive, useCancelJob, useJob, useJobEvents, useRetryJob } from '@/features/crawl-jobs/api'
import { Button, ConfirmDialog, ErrorState, fmtDate, fmtDuration, JobBadge, KV, PageHeader, Panel, Skeleton, Stat } from '@/components/ui'
import s from '@/components/platform/page.module.scss'

export default function JobDetailPage() {
  const id = useParams<{ id: string }>().id
  const router = useRouter()
  const { data: me } = useMe()
  const job = useJob(id)
  const active = isActive(job.data)
  const events = useJobEvents(id, active)
  const cancel = useCancelJob()
  const retry = useRetryJob()
  const [confirm, setConfirm] = useState(false)
  if (job.error) return <ErrorState error={job.error} onRetry={() => job.refetch()} />
  const j = job.data
  const result = (j?.result ?? {}) as Record<string, unknown>
  return (
    <>
      <PageHeader
        crumbs={[{ href: '/admin/jobs', label: 'Crawl jobs' }]}
        title={j ? <>{j.kind === 'build' ? 'Knowledge-base build' : `Crawl · ${j.source_name ?? j.source_key}`} <JobBadge status={j.status} /></> : <Skeleton w={280} h={30} />}
        description={j && <>Job <span className={s.mono}>{j.id}</span>{j.retry_of && <> · retry of <Link href={`/admin/jobs/${j.retry_of}`}>{j.retry_of.slice(0, 8)}</Link></>}</>}
        actions={j && isAdmin(me) && (
          <>
            {active && <Button variant="danger" icon={<Square size={14} />} onClick={() => setConfirm(true)} disabled={j.cancel_requested}>{j.cancel_requested ? 'Cancelling…' : 'Cancel'}</Button>}
            {['failed', 'partially_succeeded', 'cancelled'].includes(j.status) && (
              <Button icon={<RotateCcw size={14} />} loading={retry.isPending} onClick={() => retry.mutate(j.id, { onSuccess: (r) => router.push(`/admin/jobs/${r.data.job_ids[0]}`) })}>Retry</Button>
            )}
          </>
        )}
      />
      {j && (
        <div className={s.stats}>
          <Stat label="Phase" value={<span style={{ fontSize: '1.1rem' }}>{j.phase ?? '—'}</span>} hint={active ? 'updating live' : undefined} />
          <Stat label="URLs discovered" value={j.urls_discovered.toLocaleString()} />
          <Stat label="URLs processed" value={j.urls_processed.toLocaleString()} />
          <Stat label="Records extracted" value={j.records_extracted.toLocaleString()} />
          <Stat label="Errors" value={j.error_count} tone={j.error_count ? 'bad' : undefined} />
          <Stat label="Duration" value={<span style={{ fontSize: '1.1rem' }}>{fmtDuration(j.started_at, j.finished_at)}</span>} hint={`attempt ${j.attempts}`} />
        </div>
      )}
      <div className={s.grid21}>
        <Panel title="Event log" actions={active && <span className={s.muted} style={{ fontSize: '0.78rem' }}>polling every 2s</span>}>
          {events.isLoading ? <div className={s.pad}><Skeleton h={200} /></div> : (
            <ol className={s.events}>
              {events.data?.data.map((e) => (
                <li key={e.id} data-level={e.level}>
                  <span>{new Date(e.ts).toLocaleTimeString()}</span>
                  <span>{e.phase ?? ''}</span>
                  <span>{e.message}</span>
                </li>
              ))}
            </ol>
          )}
        </Panel>
        <div className={s.stack}>
          <Panel title="Details">
            <div className={s.pad}>
              {j && <KV items={[
                ['Source', j.source_id ? <Link href={`/admin/sources/${j.source_id}`}>{j.source_key} · {j.source_name}</Link> : null],
                ['Queued', fmtDate(j.created_at)], ['Started', fmtDate(j.started_at)], ['Finished', fmtDate(j.finished_at)],
                ['Error', j.error && <span style={{ color: 'var(--coral)' }}>{j.error}</span>],
                ['Parameters', Object.keys(j.params).length ? <pre className={s.code}>{JSON.stringify(j.params, null, 2)}</pre> : null],
              ]} />}
            </div>
          </Panel>
          {Object.keys(result).length > 0 && (
            <Panel title="Result">
              <div className={s.pad}><pre className={s.code}>{JSON.stringify(result, null, 2)}</pre></div>
            </Panel>
          )}
        </div>
      </div>
      <ConfirmDialog open={confirm} title="Cancel this job?" danger confirmLabel="Cancel job" body="Running crawls stop at the next fetch checkpoint; records already persisted are kept." loading={cancel.isPending}
        onCancel={() => setConfirm(false)} onConfirm={() => cancel.mutate(id, { onSettled: () => setConfirm(false) })} />
    </>
  )
}
