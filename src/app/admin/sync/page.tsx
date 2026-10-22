'use client'

import { Suspense, useState } from 'react'
import Link from 'next/link'
import { Play } from 'lucide-react'
import { type SyncRun, useChanges, useRunNow, useSyncRun, useSyncRuns, useSyncStatus, useUpdateSchedule } from '@/features/sync/api'
import { Button, EmptyState, ErrorState, fmtAgo, JobBadge, KV, PageHeader, Pagination, Panel, Select, Skeleton, Stat, Tag, Toggle } from '@/components/ui'
import { DataTable } from '@/components/ui/DataTable'
import s from '@/components/platform/page.module.scss'

const local = (d?: string | null) => (d ? new Date(d).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }) : '—')
const num = (m: Record<string, unknown>, k: string) => Number(m[k] ?? 0).toLocaleString()
const utc = (d?: string | null) => (d ? `${new Date(d).toISOString().slice(0, 16).replace('T', ' ')} UTC` : '—')

function SyncInner() {
  const st = useSyncStatus()
  const run = useRunNow()
  const sched = useUpdateSchedule()
  const [page, setPage] = useState(1)
  const runs = useSyncRuns(page)
  const [open, setOpen] = useState<string | null>(null)
  const d = st.data
  if (st.error) return <ErrorState error={st.error} onRetry={() => st.refetch()} />
  const last = d?.last_run
  const m = (last?.metrics ?? {}) as Record<string, unknown>
  return (
    <>
      <PageHeader
        title="Daily synchronization"
        description="Every 24 hours the worker re-checks every enabled source with conditional requests. New information is added, changed records are updated, and unchanged content is left untouched. A source outage never removes data."
        actions={<Button variant="primary" icon={<Play size={14} />} loading={run.isPending} disabled={!!d?.current_run} onClick={() => run.mutate()}>Run now</Button>}
      />
      {run.error && <ErrorState error={run.error} />}
      <div className={s.stats}>
        <Stat label="Scheduler" value={d ? (d.enabled ? 'Enabled' : 'Disabled') : <Skeleton w={80} h={24} />} tone={d ? (d.enabled ? 'good' : 'warn') : undefined}
          hint={d && (d.scheduler_alive ? `worker heartbeat ${fmtAgo(d.last_heartbeat_at)}` : 'no worker heartbeat in the last 10 min — is the worker running?')} />
        <Stat label="Next run" value={d ? local(d.next_run_at) : <Skeleton w={120} h={24} />}
          hint={d && `daily at ${String(d.hour_utc).padStart(2, '0')}:${String(d.minute_utc).padStart(2, '0')} UTC · ${utc(d.next_run_at)}`} />
        <Stat label="Current run" value={d?.current_run ? <JobBadge status="running" /> : 'Idle'} hint={d?.current_run ? `started ${fmtAgo(d.current_run.started_at)}` : undefined} />
        <Stat label="Last successful run" value={d ? local(d.last_successful_run_at) : <Skeleton w={120} h={24} />} />
        <Stat label="Last run" value={last ? <JobBadge status={last.status} /> : '—'} hint={last && `${last.trigger} · ${fmtAgo(last.started_at)}`} />
        <Stat label="Sources checked / changed" value={last ? `${num(m, 'sources_checked')} / ${num(m, 'sources_changed')}` : '—'} hint={last && `${num(m, 'sources_unchanged')} unchanged · ${num(m, 'sources_failed')} failed`} />
        <Stat label="Records created / updated" value={last ? `${num(m, 'records_created')} / ${num(m, 'records_updated')}` : '—'} hint={last && `${num(m, 'records_unchanged')} unchanged`} />
        <Stat label="New systems / components" value={last ? `${num(m, 'new_systems')} / ${num(m, 'new_components')}` : '—'} hint={last && `${num(m, 'new_tokens')} tokens · ${num(m, 'new_guidelines')} guidelines`} />
      </div>

      {d && (
        <Panel title="Schedule">
          <div className={s.pad} style={{ display: 'flex', flexWrap: 'wrap', gap: 16, alignItems: 'end' }}>
            <Toggle label="Run automatically every 24 hours" checked={d.enabled} onChange={(v) => sched.mutate({ enabled: v })} />
            <Select label="Time (UTC)" value={`${d.hour_utc}`} onChange={(v) => sched.mutate({ hour_utc: Number(v), minute_utc: 0 })}
              options={Array.from({ length: 24 }, (_, h) => ({ value: `${h}`, label: `${String(h).padStart(2, '0')}:00 UTC` }))} />
            <span className={s.muted} style={{ fontSize: '0.82rem' }}>The schedule is stored in the database, survives restarts and redeploys, and only one run can be in progress at a time.</span>
            {sched.error && <ErrorState error={sched.error} />}
          </div>
        </Panel>
      )}

      <Panel title="Run history" className={s.mt}>
        {runs.error ? <ErrorState error={runs.error} /> : runs.data?.data.length === 0 ? <EmptyState title="No runs yet">The first scheduled run starts at the next run time, or use Run now.</EmptyState> : (<>
          <DataTable caption="Synchronization runs" loading={runs.isFetching} rows={runs.data?.data} rowKey={(r) => r.id} onRowClick={(r) => setOpen(open === r.id ? null : r.id)}
            columns={[
              { key: 'st', header: 'Started', cell: (r: SyncRun) => <span className={s.cell}><strong>{local(r.started_at)}</strong><small>{r.trigger}{r.finished_at ? ` · ${Math.max(1, Math.round((+new Date(r.finished_at) - +new Date(r.started_at)) / 1000))} s` : ''}</small></span> },
              { key: 'status', header: 'Outcome', cell: (r: SyncRun) => <JobBadge status={r.status} /> },
              { key: 'src', header: 'Sources (changed / checked)', cell: (r: SyncRun) => `${num(r.metrics, 'sources_changed')} / ${num(r.metrics, 'sources_checked')}`, align: 'right' },
              { key: 'rec', header: 'Records +new / ~changed', cell: (r: SyncRun) => `+${num(r.metrics, 'records_created')} / ~${num(r.metrics, 'records_updated')}`, align: 'right', hideBelow: 'md' },
              { key: 'sys', header: 'New systems', cell: (r: SyncRun) => num(r.metrics, 'new_systems'), align: 'right', hideBelow: 'md' },
              { key: 'fail', header: 'Failures', cell: (r: SyncRun) => (Number(r.metrics.sources_failed ?? 0) ? <Tag>{num(r.metrics, 'sources_failed')}</Tag> : '0'), align: 'right' },
              { key: 'b', header: 'Rebuilt', cell: (r: SyncRun) => (r.built ? 'yes' : 'no — nothing changed'), hideBelow: 'lg' },
            ]} />
          {runs.data && <Pagination page={page} pageSize={15} total={runs.data.meta.total_items} totalPages={runs.data.meta.total_pages} onPage={setPage} />}
        </>)}
      </Panel>
      {open && <RunDetail id={open} />}
    </>
  )
}

function RunDetail({ id }: { id: string }) {
  const r = useSyncRun(id)
  const [page, setPage] = useState(1)
  const [change, setChange] = useState('')
  const ch = useChanges({ sync_run_id: id, change: change || null, page })
  if (r.error) return <ErrorState error={r.error} />
  const d = r.data
  const m = (d?.metrics ?? {}) as Record<string, unknown>
  return (
    <div className={s.grid21} style={{ marginTop: 16 }}>
      <Panel title="Per-source outcome">
        {!d ? <div className={s.pad}><Skeleton h={160} /></div> : (
          <DataTable caption="Sources in this run" rows={d.sources ?? []} rowKey={(x) => x.source_id}
            columns={[
              { key: 'k', header: 'Source', cell: (x) => <Link href={`/admin/sources/${x.source_id}`}>{x.key} · {x.name}</Link> },
              { key: 'o', header: 'Outcome', cell: (x) => <span className={s.row}><Tag tone={x.outcome === 'changed' ? 'accent' : x.outcome === 'failed' ? undefined : 'muted'}>{x.outcome}</Tag>{x.partial && <Tag>partial</Tag>}</span> },
              { key: 'r', header: 'New / changed / same', cell: (x) => (x.records_seen == null ? '—' : `${x.records_created ?? 0} / ${x.records_updated ?? 0} / ${x.records_unchanged ?? 0}`), align: 'right' },
              { key: 'n', header: 'Notes', cell: (x) => <small className={s.muted}>{x.error ?? x.reason ?? (x.stale_suppressed ? `${x.stale_suppressed} missing records kept for review` : x.records_preserved ? `${x.records_preserved} records preserved` : '')}{x.attempts && x.attempts > 1 ? ` · ${x.attempts} attempts` : ''}</small>, hideBelow: 'md' },
            ]} />
        )}
      </Panel>
      <div className={s.stack}>
        <Panel title="Totals">
          <div className={s.pad}>
            <KV items={[
              ['Sources checked', num(m, 'sources_checked')], ['Changed / unchanged', `${num(m, 'sources_changed')} / ${num(m, 'sources_unchanged')}`],
              ['Failed / skipped', `${num(m, 'sources_failed')} / ${num(m, 'sources_skipped')}`],
              ['Records created / updated / unchanged', `${num(m, 'records_created')} / ${num(m, 'records_updated')} / ${num(m, 'records_unchanged')}`],
              ['Records preserved during failures', num(m, 'records_preserved_on_failure')], ['Missing records kept for review', num(m, 'stale_suppressed')],
              ['New systems / components / tokens / guidelines', `${num(m, 'new_systems')} / ${num(m, 'new_components')} / ${num(m, 'new_tokens')} / ${num(m, 'new_guidelines')}`],
              ['Updated systems / components / tokens', `${num(m, 'systems_updated')} / ${num(m, 'components_updated')} / ${num(m, 'tokens_updated')}`],
              ['Duplicate candidates (new)', `${num(m, 'duplicate_candidates')} (${num(m, 'new_duplicate_candidates')})`],
              ['Rebuilt', d?.built ? 'yes' : 'no — no source content changed'], ['Next scheduled run', local(d?.next_run_at)],
            ]} />
          </div>
        </Panel>
        <Panel title="Content changes" actions={<Select label="Change" value={change} onChange={(v) => (setChange(v), setPage(1))}
          options={[{ value: '', label: 'All changes' }, ...['created', 'updated', 'staled', 'restored'].map((x) => ({ value: x, label: x }))]} />}>
          {ch.data?.data.length === 0 ? <p className={`${s.pad} ${s.muted}`}>No content changed in this run.</p> : (<>
            <ul className={s.list}>{ch.data?.data.map((c) => (
              <li key={c.id} className={s.row}><Tag tone={c.change === 'created' ? 'accent' : 'muted'}>{c.change}</Tag><span className={s.mono} style={{ fontSize: '0.76rem' }}>{c.record_type}</span>{c.title ?? c.record_key}</li>
            ))}</ul>
            {ch.data && ch.data.meta.total_items > 25 && <Pagination page={page} pageSize={25} total={ch.data.meta.total_items} totalPages={ch.data.meta.total_pages} onPage={setPage} />}
          </>)}
        </Panel>
      </div>
    </div>
  )
}

export default function SyncPage() {
  return <Suspense><SyncInner /></Suspense>
}
