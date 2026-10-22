'use client'

import { Suspense } from 'react'
import Link from 'next/link'
import { RefreshCw } from 'lucide-react'
import { type IssueKind, useQuality, useQualityIssues } from '@/features/quality/api'
import { useVerifyResources } from '@/features/design-systems/api'
import { useUrlState } from '@/hooks/useUrlState'
import { Button, EmptyState, ErrorState, PageHeader, Pagination, Panel, Skeleton, Stat } from '@/components/ui'
import s from '@/components/platform/page.module.scss'

const ORDER: { kind: IssueKind; tone: 'warn' | 'bad' | undefined; info?: boolean }[] = [
  { kind: 'duplicate_candidates', tone: 'warn' },
  { kind: 'missing_official_url', tone: 'warn' },
  { kind: 'invalid_links', tone: 'bad' },
  { kind: 'unverified_github', tone: 'warn' },
  { kind: 'orphaned_records', tone: 'bad' },
  { kind: 'extraction_failures', tone: 'bad' },
  { kind: 'needs_recrawl', tone: 'warn' },
  { kind: 'figma_not_found', tone: undefined, info: true },
  { kind: 'figma_unchecked', tone: undefined, info: true },
]
const TITLE: Record<IssueKind, string> = {
  duplicate_candidates: 'Duplicate candidates', missing_official_url: 'Missing official URL', invalid_links: 'Invalid links',
  unverified_github: 'Unverified GitHub links', orphaned_records: 'Broken relationships', extraction_failures: 'Extraction failures',
  needs_recrawl: 'Sources needing re-crawl', figma_not_found: 'No Figma file published', figma_unchecked: 'Figma not checked yet',
}

function QualityInner() {
  const u = useUrlState()
  const kind = (u.get('kind') || null) as IssueKind | null
  const page = u.getNum('page', 1)
  const q = useQuality()
  const issues = useQualityIssues(kind, page)
  const verify = useVerifyResources()
  const d = q.data
  return (
    <>
      <PageHeader
        title="Data quality"
        description="Issues computed from the canonical dataset. A missing Figma file is recorded as absence, not as an extraction failure."
        actions={<Button icon={<RefreshCw size={14} />} loading={verify.isPending} onClick={() => verify.mutate(undefined)}>Re-check all official pages</Button>}
      />
      {verify.isSuccess && <p className={s.notice} role="status">Verification queued — <Link href={`/admin/jobs/${verify.data.data.job_ids[0]}`}>follow the job</Link>.</p>}
      {q.error ? <ErrorState error={q.error} onRetry={() => q.refetch()} /> : (
        <div className={s.stats}>
          {ORDER.map(({ kind: k, tone, info }) => (
            <Stat key={k} label={TITLE[k]} value={d ? d.counts[k].toLocaleString() : <Skeleton w={50} h={26} />}
              tone={d && !info ? (d.counts[k] > 0 ? tone : 'good') : undefined} href={`/admin/quality?kind=${k}`} hint={d?.labels[k]} />
          ))}
          <Stat label="Systems with verified Figma" value={d ? d.figma_verified_systems.toLocaleString() : <Skeleton w={50} h={26} />} href="/systems?verified_resource=figma_file" hint={d && `of ${d.systems_total} canonical systems`} />
        </div>
      )}
      {kind && (
        <Panel title={TITLE[kind]} actions={<Link href="/admin/quality" className={s.muted}>Close</Link>}>
          {issues.error ? <ErrorState error={issues.error} onRetry={() => issues.refetch()} /> : !issues.data ? <div className={s.pad}><Skeleton h={160} /></div>
            : issues.data.data.length === 0 ? <EmptyState title="Nothing to fix here">No items currently match this check.</EmptyState> : (
              <>
                <ul className={s.list}>
                  {issues.data.data.map((it) => (
                    <li key={`${it.kind}-${it.id}`} style={{ display: 'grid', gap: 2 }}>
                      {it.href ? <Link href={it.href}><strong>{it.title}</strong></Link> : <strong>{it.title}</strong>}
                      {it.subtitle && <span className={s.muted} style={{ wordBreak: 'break-all' }}>{it.subtitle}</span>}
                      {it.detail && <small className={s.muted}>{it.detail}</small>}
                    </li>
                  ))}
                </ul>
                <Pagination page={page} pageSize={25} total={issues.data.meta.total_items} totalPages={issues.data.meta.total_pages} onPage={(p) => u.set({ page: p }, { resetPage: false })} />
              </>
            )}
        </Panel>
      )}
    </>
  )
}

export default function QualityPage() {
  return <Suspense><QualityInner /></Suspense>
}
