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
        title="Knowledge base overview"
        description={d ? `Live figures computed by the backend from the canonical dataset. Last crawl ${fmtAgo(d.last_crawl_at)}.` : 'Loading live metrics from the API…'}
      />
      {sum.error ? (
        <ErrorState error={sum.error} onRetry={() => sum.refetch()} />
      ) : (
        <div className={s.stats}>
          <Stat label="Canonical design systems" value={n(d?.design_systems)} href="/platform/systems" hint={d && `${d.systems_multi_source} corroborated by ≥2 sources`} />
          <Stat label="Source references" value={n(d?.source_references)} href="/platform/sources" hint={d && `directory & official listings from ${d.sources_total} sources`} />
          <Stat label="Verified systems" value={n(d?.systems_verified)} href="/platform/systems?verification=verified" hint={d && `${d.systems_partially_verified} partially verified`} tone={d && d.systems_verified > 0 ? 'good' : undefined} />
          <Stat label="Partially verified" value={n(d?.systems_partially_verified)} href="/platform/systems?verification=partially_verified" hint="some required attributes confirmed officially" />
          <Stat label="Components" value={n(d?.components)} href="/platform/components" hint={d && `${d.components_with_api} with structured APIs`} />
          <Stat label="Storybook stories" value={n(d?.storybook_stories)} href="/platform/storybook?tab=stories" hint={d && `${d.storybook_projects} projects`} />
          <Stat label="Component variants" value={n(d?.storybook_variants)} href="/platform/storybook?tab=variants" hint="from story args & argTypes" />
          <Stat label="Design tokens" value={n(d?.tokens)} href="/platform/tokens" />
          <Stat label="Guidelines & patterns" value={n(d && d.guidelines + d.patterns)} href="/platform/guidelines" hint={d && `${d.guidelines} guidelines · ${d.patterns} patterns`} />
          <Stat label="Resource links" value={n(d?.resources)} href="/platform/quality" hint={d && `${d.resources_verified} verified · GitHub on ${d.systems_with_github} · Figma on ${d.systems_with_figma} systems`} />
          <Stat label="Missing official link" value={n(d?.systems_missing_official_link)} href="/platform/systems?missing_resource=official" tone={d && d.systems_missing_official_link > 0 ? 'warn' : 'good'} hint="no website or documentation recorded" />
          <Stat label="Awaiting review" value={n(d?.review_open)} tone={d && d.review_open > 0 ? 'warn' : 'good'} href="/platform/review" hint="possible duplicates & conflicts" />
          <Stat label="Extraction errors" value={n(d?.extraction_errors)} tone={d && d.extraction_errors > 0 ? 'bad' : 'good'} href="/platform/quality?kind=extraction_failures" hint="failed jobs (30 days) + Storybook projects not indexed" />
          <Stat label="Jobs active" value={n(d?.jobs_running)} href="/platform/jobs" hint={d && `last crawl ${fmtAgo(d.last_crawl_at)}`} />
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
