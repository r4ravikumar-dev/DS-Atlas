'use client'

import { useEffect, useState } from 'react'
import { ApiError } from '@/lib/api/client'
import { isAdmin, useChangePassword, useMe } from '@/features/auth/api'
import { useAudit, useConfig, useJobHealth, useUpdateConfig } from '@/features/administration/api'
import { Button, ErrorState, Field, fmtDate, KV, PageHeader, Pagination, Panel, Select, Skeleton, Tabs, Tag } from '@/components/ui'
import { DataTable } from '@/components/ui/DataTable'
import s from '@/components/platform/page.module.scss'

type Tab = 'config' | 'account' | 'audit' | 'health'

export default function AdminPage() {
  const { data: me } = useMe()
  const [tab, setTab] = useState<Tab>('config')
  if (!isAdmin(me)) return <ErrorState error={new ApiError(403, { code: 'FORBIDDEN', message: 'Administrator role required.', details: [] }, '')} />
  return (
    <>
      <PageHeader title="Administration" description="Crawl configuration, approved domains, retention and export policy, the administrator account, audit trail and job health. Secrets are never shown here." />
      <div style={{ marginBottom: 14 }}><Tabs<Tab> value={tab} onChange={setTab} tabs={[{ value: 'config', label: 'Configuration' }, { value: 'account', label: 'Account' }, { value: 'audit', label: 'Audit trail' }, { value: 'health', label: 'Job health' }]} /></div>
      {tab === 'account' && <Account email={me!.email} />}
      {tab === 'config' && <Config />}
      {tab === 'audit' && <Audit />}
      {tab === 'health' && <Health />}
    </>
  )
}

function Account({ email }: { email: string }) {
  const change = useChangePassword()
  const [cur, setCur] = useState('')
  const [next, setNext] = useState('')
  const [confirm, setConfirm] = useState('')
  const mismatch = confirm.length > 0 && next !== confirm
  return (
    <div className={s.grid21}>
      <Panel title="Administrator account">
        <form className={s.pad} style={{ display: 'grid', gap: 12, maxWidth: 420 }}
          onSubmit={(e) => (e.preventDefault(), change.mutate({ current_password: cur, new_password: next }, { onSuccess: () => (setCur(''), setNext(''), setConfirm('')) }))}>
          <KV items={[['Signed in as', email]]} />
          <Field label="Current password"><input type="password" autoComplete="current-password" value={cur} onChange={(e) => setCur(e.target.value)} required /></Field>
          <Field label="New password" hint="At least 12 characters"><input type="password" autoComplete="new-password" minLength={12} value={next} onChange={(e) => setNext(e.target.value)} required /></Field>
          <Field label="Confirm new password" hint={mismatch ? 'Passwords do not match' : undefined}><input type="password" autoComplete="new-password" value={confirm} onChange={(e) => setConfirm(e.target.value)} required /></Field>
          {change.error && <ErrorState error={change.error} />}
          {change.isSuccess && <p role="status">Password changed. Every other session has been signed out.</p>}
          <Button type="submit" variant="primary" loading={change.isPending} disabled={mismatch || next.length < 12}>Change password</Button>
        </form>
      </Panel>
      <Panel title="Access model">
        <div className={s.pad} style={{ display: 'grid', gap: 8, fontSize: '0.86rem' }}>
          <p>This workspace has a single administrator account. There is no public registration and no other roles.</p>
          <p className={s.muted}>The first administrator is created once from the server shell (<code>manage.py bootstrap-admin</code>), which refuses to run when an administrator already exists. A forgotten password is reset from the server shell with <code>manage.py reset-admin-password</code>.</p>
        </div>
      </Panel>
    </div>
  )
}

function Config() {
  const cfg = useConfig()
  const save = useUpdateConfig()
  const [text, setText] = useState<Record<string, string>>({})
  const [parseErr, setParseErr] = useState<string | null>(null)
  useEffect(() => {
    if (cfg.data) setText({ approved_domains: cfg.data.approved_domains.join('\n'), ...Object.fromEntries(['crawl_defaults', 'retention', 'export_policy', 'schedule', 'data_quality_rules'].map((k) => [k, JSON.stringify((cfg.data as Record<string, unknown>)[k], null, 2)])) })
  }, [cfg.data])
  if (cfg.isLoading) return <Skeleton h={300} />
  if (cfg.error) return <ErrorState error={cfg.error} />
  const submit = () => {
    setParseErr(null)
    try {
      const body: Record<string, unknown> = { approved_domains: text.approved_domains.split(/\s+/).filter(Boolean) }
      for (const k of ['crawl_defaults', 'retention', 'export_policy', 'schedule', 'data_quality_rules']) body[k] = JSON.parse(text[k])
      save.mutate(body as never)
    } catch (e) {
      setParseErr(`Invalid JSON: ${(e as Error).message}`)
    }
  }
  return (
    <Panel title="Configuration" actions={<Button variant="primary" loading={save.isPending} onClick={submit}>Save changes</Button>}>
      <div className={s.pad} style={{ display: 'grid', gap: 14 }}>
        {save.error && <ErrorState error={save.error} />}
        {save.isSuccess && <p style={{ color: 'var(--mint)', fontSize: '0.84rem' }}>Saved and audited.</p>}
        {parseErr && <p role="alert" style={{ color: 'var(--coral)', fontSize: '0.84rem' }}>{parseErr}</p>}
        <div className={s.grid2}>
          <Field label="Approved domains (one per line)" hint="The crawler and source registration only reach these domains (plus SSRF checks)."><textarea rows={14} value={text.approved_domains ?? ''} onChange={(e) => setText({ ...text, approved_domains: e.target.value })} /></Field>
          <div className={s.stack}>
            {['crawl_defaults', 'retention', 'export_policy'].map((k) => <Field key={k} label={k.replace(/_/g, ' ')}><textarea rows={5} style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem' }} value={text[k] ?? ''} onChange={(e) => setText({ ...text, [k]: e.target.value })} /></Field>)}
          </div>
        </div>
        <div className={s.grid2}>
          {['schedule', 'data_quality_rules'].map((k) => <Field key={k} label={k.replace(/_/g, ' ')}><textarea rows={5} style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem' }} value={text[k] ?? ''} onChange={(e) => setText({ ...text, [k]: e.target.value })} /></Field>)}
        </div>
      </div>
    </Panel>
  )
}

function Audit() {
  const [page, setPage] = useState(1)
  const audit = useAudit(page)
  return (
    <Panel title="Audit trail">
      {audit.error ? <ErrorState error={audit.error} /> : (
        <DataTable caption="Audit events" loading={audit.isFetching} rows={audit.data?.data} rowKey={(e) => e.id}
          columns={[
            { key: 't', header: 'When', cell: (e) => fmtDate(e.ts) },
            { key: 'a', header: 'Action', cell: (e) => <span className={s.mono}>{e.action}</span> },
            { key: 'tg', header: 'Target', cell: (e) => <span className={s.mono}>{e.target_type}{e.target_id ? `:${e.target_id.slice(0, 12)}` : ''}</span>, hideBelow: 'md' },
            { key: 'd', header: 'Details', cell: (e) => <span className={s.mono} style={{ fontSize: '0.72rem' }}>{JSON.stringify(e.details).slice(0, 120)}</span>, hideBelow: 'lg' },
          ]} />
      )}
      {audit.data && <Pagination page={page} pageSize={25} total={audit.data.meta.total_items} totalPages={audit.data.meta.total_pages} onPage={setPage} />}
    </Panel>
  )
}

function Health() {
  const h = useJobHealth()
  if (h.error) return <ErrorState error={h.error} />
  if (!h.data) return <Skeleton h={160} />
  return (
    <Panel title="Job health">
      <div className={s.pad}>
        <KV items={[['Jobs by status', Object.entries(h.data.by_status).map(([k, v]) => `${k}: ${v}`).join(' · ')], ['Running with stale heartbeat', String(h.data.stale_running)], ['Oldest queued job', fmtDate(h.data.oldest_queued_at)]]} />
      </div>
    </Panel>
  )
}
