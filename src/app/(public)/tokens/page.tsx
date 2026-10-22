'use client'

import { Suspense } from 'react'
import { ArrowRight, Info } from 'lucide-react'
import { useToken, useTokenFacets, useTokenRefs, useTokens } from '@/features/tokens/api'
import { useUrlState } from '@/hooks/useUrlState'
import { Drawer, ErrorState, ExtLink, FacetFilter, KV, Missing, PageHeader, Pagination, Panel, SearchInput, Skeleton, Tag, Toggle, VerifyBadge } from '@/components/ui'
import { DataTable } from '@/components/ui/DataTable'
import s from '@/components/platform/page.module.scss'

function Swatch({ value, type }: { value?: string | null; type?: string | null }) {
  if (!value || type !== 'color' || !/^(#|rgb|hsl|oklch|oklab|lab|color\()/i.test(value)) return null
  return <span aria-hidden style={{ display: 'inline-block', width: 14, height: 14, borderRadius: 4, background: value, border: '1px solid var(--line-strong)', verticalAlign: 'middle', marginRight: 6 }} />
}

function TokensInner() {
  const u = useUrlState()
  const page = u.getNum('page', 1)
  const focus = u.getNum('focus', 0) || null
  const q = { q: u.get('q'), type: u.getAll('type'), theme: u.getAll('theme'), platform: u.getAll('platform'), group: u.getAll('group'), system: u.getAll('system'),
    has_alias: u.get('has_alias') || undefined, page, page_size: 30 }
  const list = useTokens(q)
  const facets = useTokenFacets()
  return (
    <>
      <PageHeader title="Design-token explorer" description="Source-native token names and values are preserved. ‘Resolved’ values come only from following documented aliases inside the same source; inferred types are flagged." />
      <div className={s.filters}>
        <SearchInput value={u.get('q')} onChange={(v) => u.set({ q: v })} placeholder="Search path, value or description…" />
        <FacetFilter label="System" facets={facets.data?.systems} selected={u.getAll('system')} onChange={(v) => u.set({ system: v })} />
        <FacetFilter label="Type" facets={facets.data?.types} selected={u.getAll('type')} onChange={(v) => u.set({ type: v })} />
        <FacetFilter label="Group" facets={facets.data?.groups} selected={u.getAll('group')} onChange={(v) => u.set({ group: v })} />
        <FacetFilter label="Theme" facets={facets.data?.themes} selected={u.getAll('theme')} onChange={(v) => u.set({ theme: v })} />
        <FacetFilter label="Platform" facets={facets.data?.platforms} selected={u.getAll('platform')} onChange={(v) => u.set({ platform: v })} />
        <Toggle label="Aliases only" checked={!!u.get('has_alias')} onChange={(v) => u.set({ has_alias: v ? 'true' : null })} />
        <span className={s.filterMeta}>{list.data && `${list.data.meta.total_items.toLocaleString()} tokens`}</span>
      </div>
      <Panel>
        {list.error ? <ErrorState error={list.error} onRetry={() => list.refetch()} /> : (
          <DataTable
            caption="Design tokens"
            loading={list.isFetching}
            rows={list.data?.data}
            rowKey={(t) => t.id}
            onRowClick={(t) => u.set({ focus: t.id }, { resetPage: false })}
            columns={[
              { key: 'p', header: 'Token', cell: (t) => <span className={s.cell}><strong className={s.mono}>{t.path}</strong><small>{t.design_system_name}{t.component ? ` · ${t.component}` : ''}</small></span> },
              { key: 'raw', header: 'Raw value', cell: (t) => <span className={s.mono}><Swatch value={t.raw_value} type={t.type} />{t.raw_value ?? <Missing label="no value" />}</span> },
              { key: 'res', header: 'Resolved', cell: (t) => (t.alias_of ? <span className={s.mono}><Swatch value={t.resolved_value} type={t.type} />{t.resolved_value ?? <Missing label="unresolved" />}</span> : <span className={s.muted}>—</span>), hideBelow: 'md' },
              { key: 't', header: 'Type', cell: (t) => (t.type ? <span title={t.type_inferred ? 'Inferred by the platform from name/value' : 'Declared by the source'}>{t.type}{t.type_inferred && '*'}</span> : <Missing label="—" />), hideBelow: 'md' },
              { key: 'th', header: 'Theme', cell: (t) => t.theme ?? '—', hideBelow: 'lg' },
              { key: 'src', header: 'Source', cell: (t) => <span className={s.mono}>{t.source_key}</span>, hideBelow: 'lg' },
            ]}
          />
        )}
        {list.data && <Pagination page={page} pageSize={30} total={list.data.meta.total_items} totalPages={list.data.meta.total_pages} onPage={(p) => u.set({ page: p }, { resetPage: false })} />}
      </Panel>
      <p className={s.muted} style={{ fontSize: '0.78rem', marginTop: 8 }}>* type inferred by the platform (not declared by the source).</p>
      <TokenDrawer id={focus} onClose={() => u.set({ focus: null }, { resetPage: false })} onOpen={(id) => u.set({ focus: id }, { resetPage: false })} />
    </>
  )
}

function TokenDrawer({ id, onClose, onOpen }: { id: number | null; onClose: () => void; onOpen: (id: number) => void }) {
  const t = useToken(id)
  const refs = useTokenRefs(id, 'references')
  const deps = useTokenRefs(id, 'dependents')
  const d = t.data
  return (
    <Drawer open={!!id} onClose={onClose} title={d?.path ?? 'Token'}>
      {t.isLoading ? <Skeleton h={240} /> : t.error ? <ErrorState error={t.error} /> : d && (
        <div style={{ display: 'grid', gap: 16 }}>
          <div className={s.row}><VerifyBadge status={d.verification_status} />{d.type && <Tag>{d.type}{d.type_inferred ? ' (inferred)' : ''}</Tag>}{d.theme && <Tag>{d.theme}</Tag>}</div>
          <KV items={[
            ['Design system', d.design_system_name], ['Name', <span key="n" className={s.mono}>{d.name}</span>], ['Path', <span key="p" className={s.mono}>{d.path}</span>],
            ['Raw value (source)', <span key="r" className={s.mono}><Swatch value={d.raw_value} type={d.type} />{d.raw_value ?? '—'}</span>],
            ['Alias of', d.alias_of && <span className={s.mono}>{d.alias_of}</span>],
            ['Resolved value (computed)', d.resolved_value && <span className={s.mono}><Swatch value={d.resolved_value} type={d.type} />{d.resolved_value}</span>],
            ['Description', d.description], ['Component', d.component], ['Platform', d.platform], ['Source format', d.source_format], ['Source version', d.source_version],
            ['Section', d.source_section], ['Evidence', <ExtLink key="e" href={d.source_url} />],
          ]} />
          <div className={s.notice}><Info size={16} aria-hidden /><span>{d.value_note}</span></div>
          <Panel title={`References (${refs.data?.length ?? 0})`}>
            <ul className={s.list}>
              {refs.data?.map((r) => <li key={r.id}><button className={s.mono} style={{ background: 'none', border: 0, color: 'var(--accent-text)', cursor: 'pointer', padding: 0 }} onClick={() => onOpen(r.id)}>{d.path} <ArrowRight size={11} /> {r.path}</button> = {r.raw_value}</li>)}
              {refs.data?.length === 0 && <li className={s.muted}>This token does not alias another extracted token.</li>}
            </ul>
          </Panel>
          <Panel title={`Dependents (${deps.data?.length ?? 0})`}>
            <ul className={s.list}>
              {deps.data?.slice(0, 30).map((r) => <li key={r.id}><button className={s.mono} style={{ background: 'none', border: 0, color: 'var(--accent-text)', cursor: 'pointer', padding: 0 }} onClick={() => onOpen(r.id)}>{r.path}</button></li>)}
              {deps.data?.length === 0 && <li className={s.muted}>No extracted token aliases this one.</li>}
            </ul>
          </Panel>
        </div>
      )}
    </Drawer>
  )
}

export default function TokensPage() {
  return <Suspense><TokensInner /></Suspense>
}
