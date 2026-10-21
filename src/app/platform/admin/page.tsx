'use client'

import { useEffect, useState } from 'react'
import { ApiError } from '@/lib/api/client'
import { can, useMe } from '@/features/auth/api'
import { useAudit, useConfig, useJobHealth, useUpdateConfig, useUpdateUser, useUsers } from '@/features/administration/api'
import { useCreateInvitation, useInvitations, useResendInvitation, useRevokeInvitation } from '@/features/invitations/api'
import { Button, ErrorState, Field, fmtDate, KV, PageHeader, Pagination, Panel, Select, Skeleton, Tabs, Tag } from '@/components/ui'
import { DataTable } from '@/components/ui/DataTable'
import s from '@/components/platform/page.module.scss'

type Tab = 'users' | 'invitations' | 'config' | 'audit' | 'health'

export default function AdminPage() {
  const { data: me } = useMe()
  const [tab, setTab] = useState<Tab>('users')
  if (!can(me, 'admin')) return <ErrorState error={new ApiError(403, { code: 'FORBIDDEN', message: 'Administrator role required.', details: [] }, '')} />
  return (
    <>
      <PageHeader title="Administration" description="Users and roles, invitations, crawl configuration, approved domains, retention and export policy, audit trail and job health. Secrets are never shown here." />
      <div style={{ marginBottom: 14 }}><Tabs<Tab> value={tab} onChange={setTab} tabs={[{ value: 'users', label: 'Users & roles' }, { value: 'invitations', label: 'Invitations' }, { value: 'config', label: 'Configuration' }, { value: 'audit', label: 'Audit trail' }, { value: 'health', label: 'Job health' }]} /></div>
      {tab === 'users' && <Users myId={me!.id} onGoToInvites={() => setTab('invitations')} />}
      {tab === 'invitations' && <Invitations />}
      {tab === 'config' && <Config />}
      {tab === 'audit' && <Audit />}
      {tab === 'health' && <Health />}
    </>
  )
}

function Users({ myId, onGoToInvites }: { myId: string; onGoToInvites: () => void }) {
  const users = useUsers()
  const update = useUpdateUser()
  return (
    <div className={s.grid21}>
      <Panel title="Users">
        {users.error ? <ErrorState error={users.error} /> : (
          <DataTable caption="Users" loading={users.isLoading} rows={users.data?.data} rowKey={(u) => u.id}
            columns={[
              { key: 'e', header: 'User', cell: (u) => <span className={s.cell}><strong>{u.name || u.email}</strong><small>{u.email}</small></span> },
              { key: 'r', header: 'Role', cell: (u) => u.id === myId ? <Tag tone="accent">{u.role} (you)</Tag> : (
                <Select label={`Role for ${u.email}`} value={u.role} onChange={(role) => update.mutate({ id: u.id, body: { role: role as never } })} options={['viewer', 'researcher', 'admin'].map((x) => ({ value: x, label: x }))} />) },
              { key: 'a', header: 'Active', cell: (u) => u.id === myId ? 'yes' : <Button size="sm" variant="ghost" onClick={() => update.mutate({ id: u.id, body: { is_active: !u.is_active } })}>{u.is_active ? 'Deactivate' : 'Activate'}</Button> },
              { key: 'l', header: 'Last sign-in', cell: (u) => fmtDate(u.last_login_at), hideBelow: 'md' },
            ]} />
        )}
        {update.error && <div className={s.pad}><ErrorState error={update.error} /></div>}
      </Panel>
      <Panel title="Add user">
        <div className={s.pad} style={{ display: 'grid', gap: 12 }}>
          <p className={s.muted} style={{ fontSize: '0.84rem' }}>
            To enforce single-use identity verification and eliminate unencrypted passwords, all new users must be registered via invitations.
          </p>
          <Button variant="primary" onClick={onGoToInvites}>Go to Invitations</Button>
        </div>
      </Panel>
    </div>
  )
}

function Invitations() {
  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState<string>('')
  const invQuery = useInvitations({ page, page_size: 20, ...(statusFilter ? { status: statusFilter } : {}) })
  const createInv = useCreateInvitation()
  const resendInv = useResendInvitation()
  const revokeInv = useRevokeInvitation()
  const [f, setF] = useState({ email: '', role: 'viewer' as 'viewer' | 'researcher' | 'admin', expires_in_days: 7 })
  const [successMsg, setSuccessMsg] = useState<string | null>(null)

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault()
    setSuccessMsg(null)
    createInv.mutate(
      {
        email: f.email,
        role: f.role,
        ttl_hours: f.expires_in_days * 24,
      },
      {
        onSuccess: (res) => {
          setF({ email: '', role: 'viewer', expires_in_days: 7 })
          setSuccessMsg(`Invitation dispatched to ${res.data.email} (${res.data.delivery_status}).`)
        },
      }
    )
  }

  const err = createInv.error instanceof ApiError ? createInv.error : null

  return (
    <div className={s.grid21}>
      <Panel title="Invitations" actions={
        <Select label="Filter status" value={statusFilter} onChange={setStatusFilter} options={[
          { value: '', label: 'All statuses' },
          { value: 'pending', label: 'Pending' },
          { value: 'accepted', label: 'Accepted' },
          { value: 'revoked', label: 'Revoked' },
          { value: 'expired', label: 'Expired' },
        ]} />
      }>
        {invQuery.error ? <ErrorState error={invQuery.error} /> : (
          <DataTable caption="Invitations" loading={invQuery.isLoading} rows={invQuery.data?.data} rowKey={(i) => i.id}
            columns={[
              { key: 'e', header: 'Recipient', cell: (i) => <span className={s.cell}><strong>{i.email}</strong><small>{i.role}</small></span> },
              { key: 'st', header: 'Status', cell: (i) => (
                <Tag tone={i.status === 'pending' ? 'accent' : 'muted'}>{i.status}</Tag>
              ) },
              { key: 'del', header: 'Delivery', cell: (i) => <Tag tone="muted">{i.delivery_status}</Tag>, hideBelow: 'md' },
              { key: 'exp', header: 'Expires', cell: (i) => fmtDate(i.expires_at), hideBelow: 'md' },
              { key: 'act', header: 'Actions', cell: (i) => i.status === 'pending' ? (
                <div className={s.row} style={{ gap: 4 }}>
                  <Button size="sm" variant="ghost" loading={resendInv.isPending} onClick={() => resendInv.mutate(i.id)}>Resend</Button>
                  <Button size="sm" variant="ghost" loading={revokeInv.isPending} onClick={() => revokeInv.mutate(i.id)}>Revoke</Button>
                </div>
              ) : '—' },
            ]} />
        )}
        {invQuery.data && <Pagination page={page} pageSize={20} total={invQuery.data.meta.total_items} totalPages={invQuery.data.meta.total_pages} onPage={setPage} />}
      </Panel>
      <Panel title="Issue invitation">
        <form className={s.pad} style={{ display: 'grid', gap: 12 }} onSubmit={handleCreate}>
          <p className={s.muted} style={{ fontSize: '0.84rem' }}>
            All platform users must be invited. Invitations are single-use, identity-bound, and require two-step email verification code confirmation.
          </p>
          {successMsg && (
            <div style={{ background: 'var(--panel-active)', border: '1px solid var(--accent)', borderRadius: 6, padding: 10, fontSize: '0.84rem' }}>
              <strong style={{ color: 'var(--accent)' }}>Success:</strong> {successMsg}
            </div>
          )}
          <Field label="Recipient Email" error={err?.details?.find((d) => d.field === 'email')?.reason}>
            <input type="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} placeholder="user@organization.org" required />
          </Field>
          <Field label="Role">
            <select value={f.role} onChange={(e) => setF({ ...f, role: e.target.value as never })}>
              <option value="viewer">viewer — read & search</option>
              <option value="researcher">researcher — crawl, compare, export</option>
              <option value="admin">admin — everything</option>
            </select>
          </Field>
          <Field label="Validity (days)">
            <input type="number" min={1} max={30} value={f.expires_in_days} onChange={(e) => setF({ ...f, expires_in_days: Number(e.target.value) })} />
          </Field>
          {err && <p role="alert" style={{ color: 'var(--coral)', fontSize: '0.84rem' }}>{err.message}</p>}
          <Button type="submit" variant="primary" loading={createInv.isPending}>Send invitation</Button>
        </form>
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
