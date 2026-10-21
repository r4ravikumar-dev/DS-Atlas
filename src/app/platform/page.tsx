'use client'

import Link from 'next/link'
import { useActivity, useCategories, useCoverage, useSummary } from '@/features/dashboard/api'
import { Bar, ErrorState, fmtAgo, JobBadge, PageHeader, Panel, Skeleton, SourceStatusBadge, Stat, Tag } from '@/components/ui'
import { DataTable } from '@/components/ui/DataTable'
import s from '@/components/platform/page.module.scss'

export default function DashboardPage() {
  const sum = useSummary()
  const cov = useCoverage()
  const cats = useCategories()
  const act = useActivity()
  const d = sum.data
  const n = (v?: number) => (v === undefined ? <Skeleton w={60} h={26} /> : v.toLocaleString())

  return (
    <>
      <PageHeader
        title="Research overview"
        description={d ? `All figures are computed by the backend from persisted records. Last crawl ${fmtAgo(d.last_crawl_at)}.` : 'Loading live metrics from the API…'}
      />
      {sum.error ? (
        <ErrorState error={sum.error} onRetry={() => sum.refetch()} />
      ) : (
        <div className={s.stats}>
          <Stat label="Registered sources" value={n(d?.sources_total)} href="/platform/sources" hint={d && `${d.sources_inspected} inspected · ${d.sources_never_crawled} never crawled`} />
          <Stat label="Failed / unavailable sources" value={n(d?.sources_failed)} tone={d && d.sources_failed > 0 ? 'bad' : undefined} href="/platform/sources?status=unavailable_seed__substitute_extracted" />
          <Stat label="Discovered URLs" value={n(d?.urls_discovered)} hint={d && `${d.pages_processed.toLocaleString()} processed successfully`} />
          <Stat label="Design systems" value={n(d?.design_systems)} href="/platform/systems" hint={d && `${d.systems_multi_source} corroborated by ≥2 sources`} />
          <Stat label="Component records" value={n(d?.components)} href="/platform/components" hint={d && `${d.components_with_api} with structured APIs`} />
          <Stat label="Storybook projects" value={n(d?.storybook_projects)} href="/platform/storybook" hint="showcase component libraries" />
          <Stat label="Storybook stories" value={n(d?.storybook_stories)} href="/platform/storybook?tab=stories" hint={d && `${n(d.storybook_variants)} variants extracted`} />
          <Stat label="Verified attributes" value={n(d?.attribute_evidence)} href="/platform/systems" hint="official docs verification" />
          <Stat label="Design tokens" value={n(d?.tokens)} href="/platform/tokens" />
          <Stat label="Guidelines & specs" value={n(d?.guidelines)} href="/platform/guidelines" hint={d && `${d.patterns} patterns`} />
          <Stat label="Review queue" value={n(d?.review_open)} tone={d && d.review_open > 0 ? 'warn' : 'good'} href="/platform/review" hint="duplicates & conflicts" />
          <Stat label="Stale records" value={n(d?.stale_records)} hint="not seen in the latest crawl" tone={d && d.stale_records > 0 ? 'warn' : undefined} />
          <Stat label="Jobs active" value={n(d?.jobs_running)} href="/platform/jobs" />
        </div>
      )}

      {d && (
        <Panel title="Data quality">
          <div className={s.pad} style={{ display: 'grid', gap: 4 }}>
            <Bar label="Records with evidence" value={d.quality.with_evidence_pct as number} max={100} hint={`${d.quality.with_evidence_pct}%`} />
            <Bar label="Linked to raw snapshot" value={d.quality.with_raw_snapshot_pct as number} max={100} hint={`${d.quality.with_raw_snapshot_pct}%`} />
            <Bar label="Verified (official source)" value={d.quality.verified_pct as number} max={100} hint={`${d.quality.verified_pct}%`} />
          </div>
        </Panel>
      )}

      <div className={s.grid21} style={{ marginTop: 16 }}>
        <Panel title="Extraction coverage by source" actions={<Link href="/platform/sources" className={s.muted}>All sources →</Link>}>
          {cov.error ? (
            <ErrorState error={cov.error} onRetry={() => cov.refetch()} />
          ) : (
            <DataTable
              loading={cov.isLoading}
              rows={cov.data}
              rowKey={(r) => r.id}
              caption="Coverage by source"
              columns={[
                { key: 'key', header: 'ID', cell: (r) => <span className={s.mono}>{r.key}</span>, width: '56px' },
                { key: 'name', header: 'Source', cell: (r) => <Link href={`/platform/sources/${r.id}`}>{r.name}</Link> },
                { key: 'status', header: 'Status', cell: (r) => <SourceStatusBadge status={r.status} />, hideBelow: 'md' },
                { key: 'pages', header: 'Pages ok', cell: (r) => `${r.pages_ok}/${r.pages_attempted}`, align: 'right', hideBelow: 'md' },
                { key: 'records', header: 'Records', cell: (r) => r.records.toLocaleString(), align: 'right' },
              ]}
            />
          )}
        </Panel>
        <div className={s.stack}>
          <Panel title="Recent crawler executions" actions={<Link href="/platform/jobs" className={s.muted}>All jobs →</Link>}>
            {act.isLoading ? (
              <div className={s.pad}><Skeleton h={160} /></div>
            ) : act.error ? (
              <ErrorState error={act.error} />
            ) : act.data!.jobs.length === 0 ? (
              <p className={`${s.pad} ${s.muted}`}>No jobs in the last 30 days.</p>
            ) : (
              <ul className={s.list}>
                {act.data!.jobs.slice(0, 8).map((j) => (
                  <li key={j.id} className={s.row} style={{ justifyContent: 'space-between' }}>
                    <Link href={`/platform/jobs/${j.id}`}>
                      {j.kind} {j.source_key ?? ''} <small className={s.muted}>· {fmtAgo(j.created_at)}</small>
                    </Link>
                    <JobBadge status={j.status} />
                  </li>
                ))}
              </ul>
            )}
          </Panel>
          <Panel title="Category distribution">
            <div className={s.pad}>
              {cats.isLoading ? (
                <Skeleton h={200} />
              ) : (
                cats.data?.map((c) => (
                  <Bar key={c.category} label={<span title={c.name}>{c.category} {c.name}</span>} value={c.total} max={Math.max(...cats.data.map((x) => x.total))} />
                ))
              )}
            </div>
          </Panel>
          <Panel title="Recently updated records">
            <ul className={s.list}>
              {act.data?.recent_records.slice(0, 6).map((r) => (
                <li key={r.id} className={s.row}>
                  <Tag>{r.record_type}</Tag>
                  <Link href={`/platform/records/${r.id}`} style={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {r.title}
                  </Link>
                  <span className={s.mono}>{r.source_key}</span>
                </li>
              ))}
            </ul>
          </Panel>
        </div>
      </div>
    </>
  )
}
