'use client'

import { Suspense, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Plus, RefreshCw } from 'lucide-react'
import { ApiError } from '@/lib/api/client'
import { can, useMe } from '@/features/auth/api'
import { useCrawlAll } from '@/features/crawl-jobs/api'
import { useCreateSource, useSources } from '@/features/sources/api'
import { useUrlState } from '@/hooks/useUrlState'
import { Button, ConfirmDialog, Drawer, ErrorState, Field, fmtAgo, PageHeader, Pagination, Panel, SearchInput, Select, SourceStatusBadge, Tag } from '@/components/ui'
import { DataTable } from '@/components/ui/DataTable'
import s from '@/components/platform/page.module.scss'

function SourcesInner() {
  const u = useUrlState()
  const router = useRouter()
  const { data: me } = useMe()
  const page = u.getNum('page', 1)
  const q = { q: u.get('q'), status: u.get('status'), origin: u.get('origin'), sort: u.get('sort'), page, page_size: 25 }
  const list = useSources(q)
  const crawlAll = useCrawlAll()
  const [confirm, setConfirm] = useState(false)
  const [adding, setAdding] = useState(false)

  return (
    <>
      <PageHeader
        title="Sources & crawl management"
        description="The source registry is backend-managed. Status reflects each adapter's documented outcome — a loaded landing page never counts as “fully scraped”."
        actions={
          can(me, 'researcher') && (
            <>
              <Button icon={<Plus size={15} />} onClick={() => setAdding(true)}>
                Register source
              </Button>
              <Button variant="primary" icon={<RefreshCw size={15} />} onClick={() => setConfirm(true)}>
                Crawl all
              </Button>
            </>
          )
        }
      />
      <div className={s.filters}>
        <SearchInput value={u.get('q')} onChange={(v) => u.set({ q: v })} placeholder="Search name, URL or ID…" />
        <Select label="Status" value={u.get('status')} onChange={(v) => u.set({ status: v })} options={[
          { value: '', label: 'Any status' }, { value: 'inspected', label: 'Inspected' }, { value: 'inspected_partial', label: 'Partially inspected' },
          { value: 'unavailable_seed__substitute_extracted', label: 'Unavailable (substitute)' }, { value: 'never_crawled', label: 'Never crawled' }, { value: 'failed_or_blocked', label: 'Failed / blocked' },
        ]} />
        <Select label="Origin" value={u.get('origin')} onChange={(v) => u.set({ origin: v })} options={[{ value: '', label: 'Seed + user' }, { value: 'seed', label: 'Seed sources' }, { value: 'user', label: 'User-registered' }]} />
        <span className={s.filterMeta}>{list.data && `${list.data.meta.total_items} sources`}</span>
      </div>
      <Panel>
        {list.error ? (
          <ErrorState error={list.error} onRetry={() => list.refetch()} />
        ) : (
          <DataTable
            caption="Registered sources"
            loading={list.isFetching}
            rows={list.data?.data}
            rowKey={(r) => r.id}
            onRowClick={(r) => router.push(`/platform/sources/${r.id}`)}
            sort={u.get('sort')}
            onSort={(k) => u.set({ sort: k })}
            columns={[
              { key: 'key', header: 'ID', sortKey: 'key', cell: (r) => <span className={s.mono}>{r.key}</span>, width: '64px' },
              { key: 'name', header: 'Source', sortKey: 'name', cell: (r) => (
                <span className={s.cell}><strong>{r.name}</strong><small className={s.wrapText}>{r.domain}</small></span>) },
              { key: 'type', header: 'Type', cell: (r) => <Tag>{r.source_type.replace(/_/g, ' ')}</Tag>, hideBelow: 'lg' },
              { key: 'status', header: 'Status', sortKey: 'status', cell: (r) => <span className={s.row}><SourceStatusBadge status={r.status} />{r.is_paused && <Tag>paused</Tag>}</span> },
              { key: 'pages', header: 'Pages ok', cell: (r) => `${r.pages_ok}/${r.pages_attempted}`, align: 'right', hideBelow: 'md' },
              { key: 'records', header: 'Records', sortKey: 'records', cell: (r) => r.records_count.toLocaleString(), align: 'right' },
              { key: 'errors', header: 'Errors', sortKey: 'errors', cell: (r) => (r.error_count ? <span style={{ color: 'var(--coral)' }}>{r.error_count}</span> : '0'), align: 'right', hideBelow: 'md' },
              { key: 'last', header: 'Last success', sortKey: 'last_success_at', cell: (r) => fmtAgo(r.last_success_at), hideBelow: 'lg' },
            ]}
          />
        )}
        {list.data && <Pagination page={page} pageSize={25} total={list.data.meta.total_items} totalPages={list.data.meta.total_pages} onPage={(p) => u.set({ page: p }, { resetPage: false })} />}
      </Panel>

      <ConfirmDialog
        open={confirm}
        title="Crawl every active source?"
        body="Queues one crawl job per active source plus a knowledge-base rebuild. Sources already crawling are skipped. Crawlers respect robots.txt and per-host rate limits."
        confirmLabel="Queue crawls"
        loading={crawlAll.isPending}
        onCancel={() => setConfirm(false)}
        onConfirm={() => crawlAll.mutate({ rebuild: true }, { onSuccess: (r) => (setConfirm(false), router.push(`/platform/jobs?highlight=${r.data.job_ids[0]}`)) })}
      />
      <AddSourceDrawer open={adding} onClose={() => setAdding(false)} />
    </>
  )
}

function AddSourceDrawer({ open, onClose }: { open: boolean; onClose: () => void }) {
  const create = useCreateSource()
  const router = useRouter()
  const [form, setForm] = useState({ name: '', url: 'https://', source_type: 'documentation', max_pages: 30, max_depth: 2 })
  const [touched, setTouched] = useState(false)
  const urlOk = /^https:\/\/[^\s/$.?#].[^\s]*$/i.test(form.url)
  const err = create.error instanceof ApiError ? create.error : null
  const fieldErr = (f: string) => err?.details?.find((d) => d.field === f)?.reason
  return (
    <Drawer open={open} onClose={onClose} title="Register a source">
      <form
        style={{ display: 'grid', gap: 14 }}
        onSubmit={(e) => {
          e.preventDefault()
          setTouched(true)
          if (!urlOk || form.name.trim().length < 2) return
          create.mutate(form as never, { onSuccess: (r) => (onClose(), router.push(`/platform/sources/${r.data.id}`)) })
        }}
        noValidate
      >
        <p className={s.muted} style={{ fontSize: '0.86rem' }}>
          The backend validates the URL (https only, approved domain, public address) before registering. User sources use a conservative same-host crawler.
        </p>
        <Field label="Name" error={touched && form.name.trim().length < 2 ? 'At least 2 characters.' : undefined}>
          <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} maxLength={300} />
        </Field>
        <Field label="URL" error={(touched && !urlOk ? 'Must be a valid https:// URL.' : undefined) ?? fieldErr('url')} hint="Domain must be on the approved list (Settings).">
          <input value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} inputMode="url" />
        </Field>
        <Field label="Type">
          <select value={form.source_type} onChange={(e) => setForm({ ...form, source_type: e.target.value })}>
            {['documentation', 'component_library', 'directory', 'resource_guide', 'publication', 'other'].map((t) => <option key={t} value={t}>{t.replace('_', ' ')}</option>)}
          </select>
        </Field>
        <div className={s.grid2}>
          <Field label="Max pages" hint="1–500"><input type="number" min={1} max={500} value={form.max_pages} onChange={(e) => setForm({ ...form, max_pages: Number(e.target.value) })} /></Field>
          <Field label="Max depth" hint="0–5"><input type="number" min={0} max={5} value={form.max_depth} onChange={(e) => setForm({ ...form, max_depth: Number(e.target.value) })} /></Field>
        </div>
        {err && <p role="alert" style={{ color: 'var(--coral)', fontSize: '0.86rem' }}>{err.message}</p>}
        <Button type="submit" variant="primary" loading={create.isPending}>Register</Button>
      </form>
    </Drawer>
  )
}

export default function SourcesPage() {
  return (
    <Suspense>
      <SourcesInner />
    </Suspense>
  )
}
