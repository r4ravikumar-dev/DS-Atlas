'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useParams, useRouter } from 'next/navigation'
import { Pause, Play, RefreshCw } from 'lucide-react'
import { can, useMe } from '@/features/auth/api'
import { isActive } from '@/features/crawl-jobs/api'
import { useSource, useSourceCoverage, useSourceDocuments, useSourceJobs, useStartCrawl, useUpdateSource } from '@/features/sources/api'
import { Button, ConfirmDialog, ErrorState, ExtLink, fmtAgo, fmtDate, fmtDuration, JobBadge, KV, PageHeader, Pagination, Panel, SearchInput, Select, Skeleton, SourceStatusBadge, Tabs, Tag, Toggle } from '@/components/ui'
import { DataTable } from '@/components/ui/DataTable'
import s from '@/components/platform/page.module.scss'

type Tab = 'overview' | 'urls' | 'jobs' | 'policy'

export default function SourceDetailPage() {
  const id = Number(useParams<{ id: string }>().id)
  const router = useRouter()
  const { data: me } = useMe()
  const src = useSource(id)
  const cov = useSourceCoverage(id)
  const [tab, setTab] = useState<Tab>('overview')
  const jobs = useSourceJobs(id, true)
  const running = jobs.data?.data.some(isActive) ?? false
  const crawl = useStartCrawl(id)
  const update = useUpdateSource(id)
  const [confirm, setConfirm] = useState(false)
  const [refresh, setRefresh] = useState(false)

  if (src.error) return <ErrorState error={src.error} onRetry={() => src.refetch()} />
  const d = src.data
  return (
    <>
      <PageHeader
        crumbs={[{ href: '/platform/sources', label: 'Sources' }]}
        title={d ? <>{d.name} <span className={s.mono} style={{ color: 'var(--faint)' }}>{d.key}</span></> : <Skeleton w={300} h={30} />}
        description={d && <ExtLink href={d.url} />}
        actions={
          d && can(me, 'researcher') && (
            <>
              <Button icon={d.is_paused ? <Play size={15} /> : <Pause size={15} />} loading={update.isPending} onClick={() => update.mutate({ is_paused: !d.is_paused })}>
                {d.is_paused ? 'Resume' : 'Pause'}
              </Button>
              <Button variant="primary" icon={<RefreshCw size={15} />} disabled={d.is_paused || running} onClick={() => setConfirm(true)}>
                {running ? 'Crawl in progress…' : 'Start crawl'}
              </Button>
            </>
          )
        }
      />
      {d && (
        <div className={s.stats}>
          <div className={s.cell} style={{ padding: 4 }}><small>Status</small><SourceStatusBadge status={d.status} /></div>
          <div className={s.cell}><small>Pages ok / attempted</small><strong>{d.pages_ok} / {d.pages_attempted}</strong></div>
          <div className={s.cell}><small>Current records</small><strong>{d.records_count.toLocaleString()}</strong></div>
          <div className={s.cell}><small>Errors (last crawl)</small><strong style={{ color: d.error_count ? 'var(--coral)' : undefined }}>{d.error_count}</strong></div>
          <div className={s.cell}><small>Last success</small><strong>{fmtAgo(d.last_success_at)}</strong></div>
        </div>
      )}
      <div style={{ marginBottom: 14 }}>
        <Tabs<Tab> value={tab} onChange={setTab} tabs={[{ value: 'overview', label: 'Coverage' }, { value: 'urls', label: 'Discovered URLs' }, { value: 'jobs', label: 'Crawl history', count: jobs.data?.meta.total_items }, { value: 'policy', label: 'Access policy' }]} />
      </div>

      {tab === 'overview' && (
        <div className={s.grid21}>
          <Panel title="Extraction coverage">
            <div className={s.pad}>
              {cov.isLoading || !d ? <Skeleton h={180} /> : (
                <KV items={[
                  ['Extraction method', (d.coverage as Record<string, string>).extraction_method],
                  ['Source provides', (d.coverage as Record<string, string>).provides],
                  ['Records by type', cov.data && Object.keys(cov.data.records_by_type).length ? <span className={s.row}>{Object.entries(cov.data.records_by_type).map(([k, v]) => <Tag key={k}>{k}: {v}</Tag>)}</span> : null],
                  ['URL outcomes', cov.data && Object.keys(cov.data.urls_by_outcome).length ? <span className={s.row}>{Object.entries(cov.data.urls_by_outcome).map(([k, v]) => <Tag key={k}>{k}: {v}</Tag>)}</span> : null],
                  ['Resolved URL', d.resolved_url && <ExtLink href={d.resolved_url} />],
                  ['Page title', d.page_title],
                  ['Version context', cov.data && Object.keys(cov.data.version_context).length ? <pre className={s.code}>{JSON.stringify(cov.data.version_context, null, 2)}</pre> : null],
                ]} />
              )}
            </div>
          </Panel>
          <div className={s.stack}>
            <Panel title="Documented limitations">
              <ul className={s.list}>
                {cov.data?.limitations.length ? cov.data.limitations.map((l, i) => <li key={i}>{l}</li>) : <li className={s.muted}>None recorded.</li>}
              </ul>
            </Panel>
            <Panel title={`Errors (${cov.data?.errors.length ?? 0})`}>
              <ul className={s.list}>
                {cov.data?.errors.length ? cov.data.errors.map((l, i) => <li key={i} className={s.mono} style={{ color: 'var(--coral)' }}>{l}</li>) : <li className={s.muted}>No errors in the last crawl.</li>}
              </ul>
            </Panel>
          </div>
        </div>
      )}
      {tab === 'urls' && <UrlQueue id={id} />}
      {tab === 'jobs' && (
        <Panel>
          <DataTable
            caption="Crawl history"
            loading={jobs.isLoading}
            rows={jobs.data?.data}
            rowKey={(j) => j.id}
            onRowClick={(j) => router.push(`/platform/jobs/${j.id}`)}
            columns={[
              { key: 'status', header: 'Status', cell: (j) => <JobBadge status={j.status} /> },
              { key: 'created', header: 'Queued', cell: (j) => fmtDate(j.created_at) },
              { key: 'dur', header: 'Duration', cell: (j) => fmtDuration(j.started_at, j.finished_at), hideBelow: 'md' },
              { key: 'urls', header: 'URLs ok', cell: (j) => j.urls_processed, align: 'right' },
              { key: 'rec', header: 'Records', cell: (j) => j.records_extracted.toLocaleString(), align: 'right' },
              { key: 'err', header: 'Errors', cell: (j) => j.error_count, align: 'right', hideBelow: 'md' },
            ]}
          />
        </Panel>
      )}
      {tab === 'policy' && d && (
        <div className={s.grid2}>
          <Panel title="robots.txt check">
            <div className={s.pad}>
              <KV items={[['robots.txt', <ExtLink key="r" href={(d.robots as Record<string, string>).robots_url} />], ['HTTP status', String((d.robots as Record<string, unknown>).status ?? '—')], ['Note', (d.robots as Record<string, string>).note], ['Checked', fmtDate((d.robots as Record<string, string>).checked_at)]]} />
              {(d.robots as Record<string, string>).excerpt && <pre className={s.code} style={{ marginTop: 12 }}>{(d.robots as Record<string, string>).excerpt}</pre>}
            </div>
          </Panel>
          <Panel title="Crawl limits">
            <div className={s.pad}>
              <KV items={[['Adapter', d.adapter], ['Origin', d.origin], ['Source-specific limits', Object.keys(d.crawl_limits).length ? <pre className={s.code}>{JSON.stringify(d.crawl_limits, null, 2)}</pre> : 'Platform defaults (Settings)'], ['Paused', d.is_paused ? 'Yes' : 'No']]} />
              <p className={s.muted} style={{ fontSize: '0.8rem', marginTop: 10 }}>
                Crawling never bypasses authentication, paywalls, CAPTCHAs or anti-bot controls; per-host delays honour robots <code>Crawl-delay</code>.
              </p>
            </div>
          </Panel>
        </div>
      )}

      <ConfirmDialog
        open={confirm}
        title={`Crawl ${d?.name ?? ''}?`}
        body={
          <div style={{ display: 'grid', gap: 10 }}>
            <p>A background worker will fetch allowed public pages, persist snapshots and evidence, and upsert records. A knowledge-base rebuild follows automatically.</p>
            <Toggle label="Bypass the 7-day HTTP cache (refresh)" checked={refresh} onChange={setRefresh} />
          </div>
        }
        confirmLabel="Start crawl"
        loading={crawl.isPending}
        onCancel={() => setConfirm(false)}
        onConfirm={() => crawl.mutate({ rebuild: true, refresh }, { onSuccess: (r) => (setConfirm(false), router.push(`/platform/jobs/${r.data.job_ids[0]}`)) })}
      />
      {crawl.error && <ErrorState error={crawl.error} />}
    </>
  )
}

function UrlQueue({ id }: { id: number }) {
  const [page, setPage] = useState(1)
  const [q, setQ] = useState('')
  const [outcome, setOutcome] = useState('')
  const docs = useSourceDocuments(id, { page, page_size: 25, q, outcome })
  return (
    <Panel>
      <div className={s.filters} style={{ padding: '12px 12px 0' }}>
        <SearchInput value={q} onChange={(v) => (setQ(v), setPage(1))} placeholder="Filter URLs…" />
        <Select label="Outcome" value={outcome} onChange={(v) => (setOutcome(v), setPage(1))} options={[{ value: '', label: 'Any outcome' }, ...['fetched', 'cache_hit', 'not_modified', 'http_error', 'failed', 'blocked_robots', 'blocked_unsafe_destination', 'skipped_not_allowlisted'].map((o) => ({ value: o, label: o }))]} />
      </div>
      {docs.error ? <ErrorState error={docs.error} /> : (
        <DataTable
          caption="Discovered URLs"
          loading={docs.isFetching}
          rows={docs.data?.data}
          rowKey={(r) => r.id}
          columns={[
            { key: 'url', header: 'URL', cell: (r) => <span className={s.cell}><ExtLink href={r.url} />{r.parent_url && <small className={s.wrapText}>from {r.parent_url}</small>}</span> },
            { key: 'outcome', header: 'Outcome', cell: (r) => <Tag tone={r.outcome === 'fetched' || r.outcome === 'cache_hit' ? 'accent' : undefined}>{r.outcome}</Tag> },
            { key: 'status', header: 'HTTP', cell: (r) => r.http_status ?? '—', align: 'right', hideBelow: 'md' },
            { key: 'depth', header: 'Depth', cell: (r) => r.depth, align: 'right', hideBelow: 'lg' },
            { key: 'snap', header: 'Snapshot', cell: (r) => (r.raw_document_id ? <a href={`/api/v1/documents/${r.raw_document_id}/content`} className={s.mono}>#{r.raw_document_id}</a> : '—'), hideBelow: 'md' },
            { key: 'seen', header: 'Last seen', cell: (r) => fmtAgo(r.updated_at), hideBelow: 'lg' },
          ]}
        />
      )}
      {docs.data && <Pagination page={page} pageSize={25} total={docs.data.meta.total_items} totalPages={docs.data.meta.total_pages} onPage={setPage} />}
    </Panel>
  )
}
