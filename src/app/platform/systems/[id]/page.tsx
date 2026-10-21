'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useParams, useRouter } from 'next/navigation'
import { Pencil } from 'lucide-react'
import { can, useMe } from '@/features/auth/api'
import { useSystem, useSystemComponents, useSystemGuidelines, useSystemSources, useSystemTokens, useUpdateSystem } from '@/features/design-systems/api'
import { Button, Drawer, ErrorState, ExtLink, Field, fmtDate, KV, Missing, PageHeader, Pagination, Panel, Skeleton, Tabs, Tag, VerifyBadge } from '@/components/ui'
import { DataTable } from '@/components/ui/DataTable'
import s from '@/components/platform/page.module.scss'

type Tab = 'components' | 'tokens' | 'guidelines' | 'sources'

export default function SystemDetailPage() {
  const id = Number(useParams<{ id: string }>().id)
  const router = useRouter()
  const { data: me } = useMe()
  const sys = useSystem(id)
  const [tab, setTab] = useState<Tab>('components')
  const [page, setPage] = useState(1)
  const comps = useSystemComponents(id, tab === 'components' ? page : 1)
  const toks = useSystemTokens(id, tab === 'tokens' ? page : 1)
  const gls = useSystemGuidelines(id, tab === 'guidelines' ? page : 1)
  const srcs = useSystemSources(id)
  const [editing, setEditing] = useState(false)
  if (sys.error) return <ErrorState error={sys.error} onRetry={() => sys.refetch()} />
  const d = sys.data
  const attrs = (d?.attributes ?? {}) as Record<string, any> // eslint-disable-line @typescript-eslint/no-explicit-any
  const cov = attrs.documentation_coverage ?? {}
  return (
    <>
      <PageHeader
        crumbs={[{ href: '/platform/systems', label: 'Design systems' }]}
        title={d ? d.name : <Skeleton w={260} h={30} />}
        description={d && <span className={s.row}>{d.organization && <span>{d.organization}</span>}<VerifyBadge status={d.verification_status} /><span className={s.muted}>{d.verification_basis}</span></span>}
        actions={d && can(me, 'researcher') && <Button icon={<Pencil size={14} />} onClick={() => setEditing(true)}>Edit description</Button>}
      />
      {d && (
        <div className={s.grid21}>
          <Panel title="Profile">
            <div className={s.pad}>
              {d.description ? <p style={{ marginBottom: 12 }}>{d.description}</p> : <p style={{ marginBottom: 12 }}><Missing label="No description extracted from sources" /></p>}
              <KV items={[
                ['Documentation', d.documentation_url && <ExtLink href={d.documentation_url} />],
                ['Repository', d.repository_url && <ExtLink href={d.repository_url} />],
                ['Storybook', d.storybook_url && <ExtLink href={d.storybook_url} />],
                ['Design resources', d.design_resource_url && <ExtLink href={d.design_resource_url} />],
                ['Frameworks', d.frameworks.length ? <span className={s.row}>{d.frameworks.map((f) => <Tag key={f}>{f}</Tag>)}</span> : null],
                ['Styling strategy', d.styling_strategy], ['Token architecture', d.token_architecture], ['Accessibility documentation', d.accessibility_documentation],
                ['Governance', d.governance], ['AI-readiness score', d.ai_readiness !== null ? `${d.ai_readiness} / 5 (DesignSystems.one)` : null],
                ['Aliases', d.aliases.length ? d.aliases.join(', ') : null], ['Last verified', fmtDate(d.last_verified_at)],
              ]} />
            </div>
          </Panel>
          <div className={s.stack}>
            <Panel title="Provenance">
              <div className={s.pad}>
                <KV items={[
                  ['Independent sources', <span key="s" className={s.row}>{d.source_keys.map((k) => <Tag key={k}>{k}</Tag>)}</span>],
                  ['Surf: foundations / components', cov.surf_foundations_claimed !== undefined && cov.surf_foundations_claimed !== null ? `${cov.surf_foundations_claimed} / ${cov.surf_components_claimed}` : null],
                  ['Storybook component count', cov.storybook_component_count],
                ]} />
              </div>
            </Panel>
            {Object.keys(d.conflicts).length > 0 && (
              <Panel title="Conflicting claims (unresolved)">
                <div className={s.pad}><pre className={s.code}>{JSON.stringify(d.conflicts, null, 2)}</pre>
                  <p className={s.muted} style={{ fontSize: '0.8rem', marginTop: 8 }}>Conflicts are recorded, not silently resolved. See the <Link href="/platform/review">review queue</Link>.</p></div>
              </Panel>
            )}
          </div>
        </div>
      )}
      <div style={{ margin: '18px 0 12px' }}>
        <Tabs<Tab> value={tab} onChange={(t) => (setTab(t), setPage(1))} tabs={[
          { value: 'components', label: 'Components', count: comps.data?.meta.total_items },
          { value: 'tokens', label: 'Tokens', count: toks.data?.meta.total_items },
          { value: 'guidelines', label: 'Guidelines', count: gls.data?.meta.total_items },
          { value: 'sources', label: 'Source records', count: srcs.data?.length },
        ]} />
      </div>
      <Panel>
        {tab === 'components' && (<>
          <DataTable caption="Components" loading={comps.isFetching} rows={comps.data?.data} rowKey={(r) => r.id} onRowClick={(r) => router.push(`/platform/components/${r.id}`)}
            columns={[
              { key: 'n', header: 'Component', cell: (r) => <span className={s.cell}><strong>{r.name}</strong><small>{r.family ?? 'unclassified'}</small></span> },
              { key: 'lvl', header: 'Detail', cell: (r) => <Tag>{r.detail_level}</Tag> },
              { key: 'p', header: 'Props', cell: (r) => r.props_count, align: 'right' },
              { key: 'src', header: 'Source', cell: (r) => <span className={s.mono}>{r.source_key}</span>, hideBelow: 'md' },
            ]} />
          {comps.data && <Pagination page={page} pageSize={20} total={comps.data.meta.total_items} totalPages={comps.data.meta.total_pages} onPage={setPage} />}
        </>)}
        {tab === 'tokens' && (<>
          <DataTable caption="Tokens" loading={toks.isFetching} rows={toks.data?.data} rowKey={(r) => r.id} onRowClick={(r) => router.push(`/platform/tokens?focus=${r.id}`)}
            columns={[
              { key: 'p', header: 'Token', cell: (r) => <span className={s.mono}>{r.path}</span> },
              { key: 'v', header: 'Raw value', cell: (r) => <span className={s.mono}>{r.raw_value ?? '—'}</span> },
              { key: 't', header: 'Type', cell: (r) => r.type ?? <Missing />, hideBelow: 'md' },
              { key: 'th', header: 'Theme', cell: (r) => r.theme ?? '—', hideBelow: 'md' },
            ]} />
          {toks.data && <Pagination page={page} pageSize={20} total={toks.data.meta.total_items} totalPages={toks.data.meta.total_pages} onPage={setPage} />}
        </>)}
        {tab === 'guidelines' && (<>
          <DataTable caption="Guidelines" loading={gls.isFetching} rows={gls.data?.data} rowKey={(r) => r.id}
            onRowClick={(r) => router.push(`/platform/${r.record_type === 'pattern' ? 'patterns' : 'guidelines'}/${r.id}`)}
            columns={[
              { key: 't', header: 'Title', cell: (r) => r.title },
              { key: 'c', header: 'Category', cell: (r) => <Tag>{r.category} {r.category_name}</Tag>, hideBelow: 'md' },
              { key: 'v', header: 'Verification', cell: (r) => <VerifyBadge status={r.verification_status} /> },
            ]} />
          {gls.data && <Pagination page={page} pageSize={20} total={gls.data.meta.total_items} totalPages={gls.data.meta.total_pages} onPage={setPage} />}
        </>)}
        {tab === 'sources' && (
          <DataTable caption="Source records" loading={srcs.isLoading} rows={srcs.data} rowKey={(r) => r.record_id}
            columns={[
              { key: 'k', header: 'Source', cell: (r) => <Link href={`/platform/sources/${r.source_id}`}>{r.source_key} · {r.source_name}</Link> },
              { key: 't', header: 'Listing', cell: (r) => <Link href={`/platform/records/${r.record_id}`}>{r.title}</Link> },
              { key: 'e', header: 'Evidence', cell: (r) => <ExtLink href={r.evidence_url} />, hideBelow: 'md' },
              { key: 'v', header: 'Verification', cell: (r) => <VerifyBadge status={r.verification_status} /> },
            ]} />
        )}
      </Panel>
      {d && <EditDrawer open={editing} onClose={() => setEditing(false)} id={id} initial={d.description ?? ''} />}
    </>
  )
}

function EditDrawer({ open, onClose, id, initial }: { open: boolean; onClose: () => void; id: number; initial: string }) {
  const upd = useUpdateSystem(id)
  const [text, setText] = useState(initial)
  return (
    <Drawer open={open} onClose={onClose} title="Edit description">
      <form style={{ display: 'grid', gap: 12 }} onSubmit={(e) => (e.preventDefault(), upd.mutate({ description: text }, { onSuccess: onClose }))}>
        <p className={s.muted} style={{ fontSize: '0.84rem' }}>Curator edits are audited and marked on the record. Provenance fields are derived from sources and cannot be edited.</p>
        <Field label="Description" hint={`${text.length}/5000`}><textarea value={text} maxLength={5000} rows={8} onChange={(e) => setText(e.target.value)} /></Field>
        {upd.error && <ErrorState error={upd.error} />}
        <Button type="submit" variant="primary" loading={upd.isPending}>Save</Button>
      </form>
    </Drawer>
  )
}
