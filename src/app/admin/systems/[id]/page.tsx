'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useParams, useRouter } from 'next/navigation'
import { Info, Pencil } from 'lucide-react'
import { isAdmin, useMe } from '@/features/auth/api'
import { useSystem, useSystemComponents, useSystemEvidence, useSystemGuidelines, useSystemSources, useSystemTokens, useUpdateSystem } from '@/features/design-systems/api'
import { useStorybookStories, useStorybookVariants } from '@/features/storybook/api'
import { Button, Drawer, EmptyState, ErrorState, ExtLink, Field, fmtDate, KV, Missing, PageHeader, Pagination, Panel, Skeleton, Tabs, Tag, VerifyBadge } from '@/components/ui'
import { DataTable } from '@/components/ui/DataTable'
import { ResourceLinks } from '@/components/platform/ResourceLinks'
import type { SystemDetail } from '@/lib/api/types'
import { ResourcesPanel } from './ResourcesPanel'
import { AssetsPanel } from './AssetsPanel'
import s from '@/components/platform/page.module.scss'

type Tab = 'components' | 'variants' | 'tokens' | 'guidelines' | 'storybook' | 'evidence' | 'sources'

export default function SystemDetailPage() {
  const id = Number(useParams<{ id: string }>().id)
  const router = useRouter()
  const sys = useSystem(id)
  const [tab, setTab] = useState<Tab>('components')
  const [page, setPage] = useState(1)
  const [editing, setEditing] = useState(false)
  const admin = isAdmin(useMe().data) // UI hint only: the API refuses writes from anyone else
  const d = sys.data
  const sid = d?.id ?? id // an old (merged) id resolves to its canonical system
  const comps = useSystemComponents(sid, tab === 'components' ? page : 1)
  const toks = useSystemTokens(sid, tab === 'tokens' ? page : 1)
  const gls = useSystemGuidelines(sid, tab === 'guidelines' ? page : 1)
  const evs = useSystemEvidence(sid, tab === 'evidence' ? page : 1)
  const srcs = useSystemSources(sid)
  const stories = useStorybookStories({ system_id: sid, page: tab === 'storybook' ? page : 1, page_size: 20 })
  const variants = useStorybookVariants({ system_id: sid, page: tab === 'variants' ? page : 1, page_size: 20 })
  if (sys.error) return <ErrorState error={sys.error} onRetry={() => sys.refetch()} />
  const cov = (d?.verification_coverage ?? {}) as { verified_required?: number; required?: number; missing_required?: string[] }
  return (
    <>
      <PageHeader
        crumbs={[{ href: '/admin/systems', label: 'Design systems' }]}
        title={d ? d.name : <Skeleton w={260} h={30} />}
        description={d && <span className={s.row}>{d.organization ? <span>{d.organization}</span> : <Missing label="Organization not recorded" />}<VerifyBadge status={d.verification_status} /></span>}
        actions={d && admin && <Button icon={<Pencil size={14} />} onClick={() => setEditing(true)}>Edit details</Button>}
      />
      {d?.requested_alias && (
        <p className={s.notice} role="status"><Info size={16} aria-hidden />
          Record #{String(d.requested_alias.id)} ({String(d.requested_alias.name ?? d.requested_alias.key)}) was merged into this canonical system. Its sources, links and related records are shown here.
        </p>
      )}
      {!d ? <Skeleton h={220} /> : (
        <>
          <div className={s.grid21}>
            <Panel title="Overview">
              <div className={s.pad}>
                {d.description ? <p style={{ marginBottom: 12 }}>{d.description}</p> : <p style={{ marginBottom: 12 }}><Missing label="No description collected" /></p>}
                <div style={{ marginBottom: 14 }}><ResourceLinks links={d.links} /></div>
                <KV items={[
                  ['Technologies', d.frameworks.length ? <span className={s.row}>{d.frameworks.map((f) => <Tag key={f}>{f}</Tag>)}</span> : null],
                  ['Platforms', d.platforms.length ? <span className={s.row}>{d.platforms.map((f) => <Tag key={f}>{f}</Tag>)}</span> : null],
                  ['Styling approach', d.styling_strategy], ['Token architecture', d.token_architecture],
                  ['Accessibility documentation', d.accessibility_documentation], ['Governance', d.governance],
                  ['Also known as', d.aliases.filter((a) => a !== d.name).length ? d.aliases.filter((a) => a !== d.name).join(', ') : null],
                  ['Consolidated records', d.merged_aliases.length ? `${d.merged_aliases.length} merged: ${d.merged_aliases.map((a) => a.name).join(', ')}` : null],
                ]} />
              </div>
            </Panel>
            <Panel title="Verification & crawl status">
              <div className={s.pad}>
                <KV items={[
                  ['Status', <span key="v" className={s.row}><VerifyBadge status={d.verification_status} /><span className={s.muted}>{d.verification_basis}</span></span>],
                  ['Required attributes verified', cov.required ? `${cov.verified_required ?? 0} / ${cov.required}` : <Missing label="No official evidence recorded yet" />],
                  ['Field-level evidence', `${evs.data?.meta.total_items ?? '…'} rows`],
                  ['Listed by sources', <span key="s" className={s.row}>{d.source_keys.map((k) => <Tag key={k}>{k}</Tag>)}</span>],
                  ['Resource links', `${d.resource_count} (${d.resources.filter((r) => r.verification_status === 'verified').length} verified)`],
                  ['Storybook', d.storybook_projects.length ? `${d.storybook_projects.length} project(s), ${d.story_count} stories, ${d.variant_count} variants` : <Missing label="No Storybook project linked" />],
                  ['Content last changed', fmtDate(d.content_updated_at ?? d.updated_at)],
                  ['Last verified against sources', fmtDate(d.last_verified_at)],
                ]} />
                {Object.keys(d.conflicts).length > 0 && (
                  <details style={{ marginTop: 12 }}>
                    <summary>Unresolved conflicting claims ({Object.keys(d.conflicts).length})</summary>
                    <pre className={s.code}>{JSON.stringify(d.conflicts, null, 2)}</pre>
                  </details>
                )}
              </div>
            </Panel>
          </div>
          <div style={{ marginTop: 14 }}><ResourcesPanel system={d} admin={admin} /></div>
          {admin && <div style={{ marginTop: 14 }}><AssetsPanel systemId={d.id} /></div>}
        </>
      )}
      <div style={{ margin: '18px 0 12px' }}>
        <Tabs<Tab> value={tab} onChange={(t) => (setTab(t), setPage(1))} tabs={[
          { value: 'components', label: 'Components', count: comps.data?.meta.total_items },
          { value: 'variants', label: 'Variants & API', count: variants.data?.meta.total_items },
          { value: 'tokens', label: 'Design tokens', count: toks.data?.meta.total_items },
          { value: 'guidelines', label: 'Patterns & guidelines', count: gls.data?.meta.total_items },
          { value: 'storybook', label: 'Storybook', count: stories.data?.meta.total_items },
          { value: 'evidence', label: 'Evidence', count: evs.data?.meta.total_items },
          { value: 'sources', label: 'Source references', count: srcs.data?.length },
        ]} />
      </div>
      <Panel>
        {tab === 'components' && (comps.data?.meta.total_items === 0 ? <EmptyState title="No components collected for this system" /> : <>
          <DataTable caption="Components" loading={comps.isFetching} rows={comps.data?.data} rowKey={(r) => r.id} onRowClick={(r) => router.push(`/admin/components/${r.id}`)}
            columns={[
              { key: 'n', header: 'Component', cell: (r) => <span className={s.cell}><strong>{r.name}</strong><small>{r.family ?? 'unclassified'}</small></span> },
              { key: 'lvl', header: 'Detail', cell: (r) => <Tag>{r.detail_level}</Tag> },
              { key: 'p', header: 'Props', cell: (r) => r.props_count, align: 'right' },
              { key: 'doc', header: 'Documentation', cell: (r) => <ExtLink href={r.documentation_url} />, hideBelow: 'lg' },
              { key: 'src', header: 'Source', cell: (r) => <span className={s.mono}>{r.source_key}</span>, hideBelow: 'md' },
            ]} />
          {comps.data && <Pagination page={page} pageSize={20} total={comps.data.meta.total_items} totalPages={comps.data.meta.total_pages} onPage={setPage} />}
        </>)}
        {tab === 'variants' && (variants.data?.meta.total_items === 0 ? <EmptyState title="No component variants extracted">Variants come from Storybook story args and argTypes.</EmptyState> : <>
          <DataTable caption="Component variants" loading={variants.isFetching} rows={variants.data?.data} rowKey={(r) => r.id}
            columns={[
              { key: 'c', header: 'Component', cell: (r) => r.component_id ? <Link href={`/admin/components/${r.component_id}`}>{r.component_name}</Link> : (r.component_name ?? <Missing />) },
              { key: 'l', header: 'Variant', cell: (r) => <strong>{r.label}</strong> },
              { key: 'p', header: 'Props', cell: (r) => <span className={s.mono} style={{ fontSize: '0.76rem' }}>{JSON.stringify(r.props).slice(0, 140)}</span>, hideBelow: 'md' },
              { key: 'm', header: 'Method', cell: (r) => <Tag tone={r.confidence === 'high' ? 'accent' : 'muted'}>{r.method} · {r.confidence}</Tag> },
            ]} />
          {variants.data && <Pagination page={page} pageSize={20} total={variants.data.meta.total_items} totalPages={variants.data.meta.total_pages} onPage={setPage} />}
        </>)}
        {tab === 'tokens' && (toks.data?.meta.total_items === 0 ? <EmptyState title="No design tokens collected for this system" /> : <>
          <DataTable caption="Tokens" loading={toks.isFetching} rows={toks.data?.data} rowKey={(r) => r.id} onRowClick={(r) => router.push(`/tokens/${r.id}`)}
            columns={[
              { key: 'p', header: 'Token', cell: (r) => <span className={s.mono}>{r.path}</span> },
              { key: 'v', header: 'Raw value', cell: (r) => <span className={s.mono}>{r.raw_value ?? '—'}</span> },
              { key: 't', header: 'Type', cell: (r) => r.type ?? <Missing />, hideBelow: 'md' },
              { key: 'th', header: 'Theme', cell: (r) => r.theme ?? '—', hideBelow: 'md' },
            ]} />
          {toks.data && <Pagination page={page} pageSize={20} total={toks.data.meta.total_items} totalPages={toks.data.meta.total_pages} onPage={setPage} />}
        </>)}
        {tab === 'guidelines' && (gls.data?.meta.total_items === 0 ? <EmptyState title="No patterns or guidelines collected for this system" /> : <>
          <DataTable caption="Patterns and guidelines" loading={gls.isFetching} rows={gls.data?.data} rowKey={(r) => r.id}
            onRowClick={(r) => router.push(`/${r.record_type === 'pattern' ? 'patterns' : 'guidelines'}/${r.id}`)}
            columns={[
              { key: 't', header: 'Title', cell: (r) => r.title },
              { key: 'k', header: 'Kind', cell: (r) => <Tag>{r.record_type}</Tag> },
              { key: 'c', header: 'Category', cell: (r) => <Tag>{r.category} {r.category_name}</Tag>, hideBelow: 'md' },
              { key: 'v', header: 'Verification', cell: (r) => <VerifyBadge status={r.verification_status} /> },
            ]} />
          {gls.data && <Pagination page={page} pageSize={20} total={gls.data.meta.total_items} totalPages={gls.data.meta.total_pages} onPage={setPage} />}
        </>)}
        {tab === 'storybook' && (!d?.storybook_projects.length ? <EmptyState title="No Storybook project linked to this system" /> : <>
          <div className={s.pad} style={{ display: 'grid', gap: 6, borderBottom: '1px solid var(--line)' }}>
            {d.storybook_projects.map((p) => (
              <div key={String(p.id)} className={s.row}>
                <strong>{String(p.title)}</strong><ExtLink href={(p.resolved_url ?? p.storybook_url) as string} />
                <Tag>{String(p.status)}</Tag><span className={s.muted}>{String(p.stories_extracted)} stories · {String(p.variants_extracted)} variants</span>
                {typeof p.limitation === 'string' && p.limitation && <small className={s.muted}>{p.limitation}</small>}
              </div>
            ))}
          </div>
          {stories.data?.meta.total_items === 0 ? <EmptyState title="No stories enumerated">The project does not expose a public story index.</EmptyState> : <>
            <DataTable caption="Stories" loading={stories.isFetching} rows={stories.data?.data} rowKey={(r) => r.id}
              columns={[
                { key: 't', header: 'Story', cell: (r) => <span className={s.cell}><strong>{r.name}</strong><small>{r.title}</small></span> },
                { key: 'e', header: 'Type', cell: (r) => <Tag>{r.entry_type}</Tag> },
                { key: 'c', header: 'Component', cell: (r) => r.component_id ? <Link href={`/admin/components/${r.component_id}`}>{r.component_name}</Link> : (r.component_name ?? '—'), hideBelow: 'md' },
                { key: 'u', header: 'Open', cell: (r) => <ExtLink href={r.story_url}>Storybook</ExtLink>, hideBelow: 'md' },
              ]} />
            {stories.data && <Pagination page={page} pageSize={20} total={stories.data.meta.total_items} totalPages={stories.data.meta.total_pages} onPage={setPage} />}
          </>}
        </>)}
        {tab === 'evidence' && (evs.data?.meta.total_items === 0 ? <EmptyState title="No field-level evidence recorded">Evidence is recorded when the system's official documentation is crawled.</EmptyState> : <>
          <DataTable caption="Field-level attribute evidence" loading={evs.isFetching} rows={evs.data?.data} rowKey={(r) => r.id}
            columns={[
              { key: 'p', header: 'Attribute', cell: (r) => <span className={s.mono}><strong>{r.attribute_path}</strong></span> },
              { key: 'v', header: 'Value', cell: (r) => <span className={s.mono} style={{ fontSize: '0.8rem' }}>{JSON.stringify(r.value)}</span> },
              { key: 'st', header: 'Status', cell: (r) => <VerifyBadge status={r.verification_status} /> },
              { key: 'url', header: 'Official source', cell: (r) => <ExtLink href={r.source_url}>{r.source_section || 'Documentation'}</ExtLink>, hideBelow: 'md' },
            ]} />
          {evs.data && <Pagination page={page} pageSize={20} total={evs.data.meta.total_items} totalPages={evs.data.meta.total_pages} onPage={setPage} />}
        </>)}
        {tab === 'sources' && (
          <DataTable caption="Source references" loading={srcs.isLoading} rows={srcs.data} rowKey={(r) => r.record_id}
            columns={[
              { key: 'k', header: 'Source', cell: (r) => <Link href={`/admin/sources/${r.source_id}`}>{r.source_key} · {r.source_name}</Link> },
              { key: 't', header: 'Listing', cell: (r) => <Link href={`/admin/records/${r.record_id}`}>{r.title}</Link> },
              { key: 'e', header: 'Original URL', cell: (r) => <ExtLink href={r.evidence_url} />, hideBelow: 'md' },
              { key: 'v', header: 'Verification', cell: (r) => <VerifyBadge status={r.verification_status} /> },
            ]} />
        )}
      </Panel>
      {d && admin && <EditDrawer open={editing} onClose={() => setEditing(false)} system={d} />}
    </>
  )
}

const list = (v: string) => v.split(',').map((x) => x.trim()).filter(Boolean)

function EditDrawer({ open, onClose, system }: { open: boolean; onClose: () => void; system: SystemDetail }) {
  const upd = useUpdateSystem(system.id)
  const [f, setF] = useState({
    name: system.name, organization: system.organization ?? '', description: system.description ?? '',
    frameworks: system.frameworks.join(', '), platforms: system.platforms.join(', '), styling_strategy: system.styling_strategy ?? '',
  })
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setF({ ...f, [k]: e.target.value })
  return (
    <Drawer open={open} onClose={onClose} title="Edit details">
      <form style={{ display: 'grid', gap: 12 }} onSubmit={(e) => (e.preventDefault(), upd.mutate({
        name: f.name.trim(), organization: f.organization.trim() || null, description: f.description.trim() || null,
        frameworks: list(f.frameworks), platforms: list(f.platforms), styling_strategy: f.styling_strategy.trim() || null,
      }, { onSuccess: onClose }))}>
        <p className={s.muted} style={{ fontSize: '0.84rem' }}>Edits are audited and stored as curated values, so knowledge-base rebuilds keep them. Links are managed in Official resources.</p>
        <Field label="Name"><input value={f.name} onChange={set('name')} required maxLength={300} /></Field>
        <Field label="Organization"><input value={f.organization} onChange={set('organization')} maxLength={300} /></Field>
        <Field label="Description" hint={`${f.description.length}/5000`}><textarea value={f.description} maxLength={5000} rows={6} onChange={set('description')} /></Field>
        <Field label="Technologies" hint="Comma-separated, e.g. React, Web Components"><input value={f.frameworks} onChange={set('frameworks')} /></Field>
        <Field label="Platforms" hint="Comma-separated, e.g. Web, iOS, Android"><input value={f.platforms} onChange={set('platforms')} /></Field>
        <Field label="Styling approach"><input value={f.styling_strategy} onChange={set('styling_strategy')} maxLength={200} /></Field>
        {upd.error && <ErrorState error={upd.error} />}
        <Button type="submit" variant="primary" loading={upd.isPending}>Save</Button>
      </form>
    </Drawer>
  )
}
