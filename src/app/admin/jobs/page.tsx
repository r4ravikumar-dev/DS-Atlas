'use client'

import { Suspense } from 'react'
import { useRouter } from 'next/navigation'
import { Hammer } from 'lucide-react'
import { isAdmin, useMe } from '@/features/auth/api'
import { useJobs, useRebuild } from '@/features/crawl-jobs/api'
import { useUrlState } from '@/hooks/useUrlState'
import { Button, ErrorState, fmtDate, fmtDuration, JobBadge, PageHeader, Pagination, Panel, Select } from '@/components/ui'
import { DataTable } from '@/components/ui/DataTable'
import s from '@/components/platform/page.module.scss'

function JobsInner() {
  const u = useUrlState()
  const router = useRouter()
  const { data: me } = useMe()
  const page = u.getNum('page', 1)
  const jobs = useJobs({ status: u.get('status'), kind: u.get('kind'), page, page_size: 25 })
  const rebuild = useRebuild()
  return (
    <>
      <PageHeader
        title="Crawl jobs"
        description="Durable background jobs persisted in PostgreSQL. Lists auto-refresh while any job is queued or running."
        actions={isAdmin(me) && <Button icon={<Hammer size={15} />} loading={rebuild.isPending} onClick={() => rebuild.mutate(undefined, { onSuccess: (r) => router.push(`/admin/jobs/${r.data.job_ids[0]}`) })}>Rebuild knowledge base</Button>}
      />
      <div className={s.filters}>
        <Select label="Kind" value={u.get('kind')} onChange={(v) => u.set({ kind: v })} options={[{ value: '', label: 'Crawl + build' }, { value: 'crawl', label: 'Crawl' }, { value: 'build', label: 'Build' }]} />
        <Select label="Status" value={u.get('status')} onChange={(v) => u.set({ status: v })} options={[{ value: '', label: 'Any status' }, ...['queued', 'running', 'succeeded', 'partially_succeeded', 'failed', 'cancelled'].map((x) => ({ value: x, label: x.replace('_', ' ') }))]} />
        <span className={s.filterMeta}>{jobs.data && `${jobs.data.meta.total_items} jobs`}</span>
      </div>
      <Panel>
        {jobs.error ? <ErrorState error={jobs.error} onRetry={() => jobs.refetch()} /> : (
          <DataTable
            caption="Jobs"
            loading={jobs.isLoading}
            rows={jobs.data?.data}
            rowKey={(j) => j.id}
            onRowClick={(j) => router.push(`/admin/jobs/${j.id}`)}
            columns={[
              { key: 'kind', header: 'Job', cell: (j) => <span className={s.cell}><strong>{j.kind}{j.source_key ? ` · ${j.source_key}` : ''}</strong><small>{j.source_name ?? (j.kind === 'build' ? 'Knowledge-base build' : '')}</small></span> },
              { key: 'status', header: 'Status', cell: (j) => <JobBadge status={j.status} /> },
              { key: 'phase', header: 'Phase', cell: (j) => <span className={s.mono}>{j.phase ?? '—'}</span>, hideBelow: 'lg' },
              { key: 'created', header: 'Queued', cell: (j) => fmtDate(j.created_at), hideBelow: 'md' },
              { key: 'dur', header: 'Duration', cell: (j) => fmtDuration(j.started_at, j.finished_at), hideBelow: 'md' },
              { key: 'urls', header: 'URLs ok', cell: (j) => j.urls_processed, align: 'right' },
              { key: 'rec', header: 'Records', cell: (j) => j.records_extracted.toLocaleString(), align: 'right' },
              { key: 'err', header: 'Errors', cell: (j) => j.error_count, align: 'right', hideBelow: 'md' },
            ]}
          />
        )}
        {jobs.data && <Pagination page={page} pageSize={25} total={jobs.data.meta.total_items} totalPages={jobs.data.meta.total_pages} onPage={(p) => u.set({ page: p }, { resetPage: false })} />}
      </Panel>
    </>
  )
}

export default function JobsPage() {
  return <Suspense><JobsInner /></Suspense>
}
