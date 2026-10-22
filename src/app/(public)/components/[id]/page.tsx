'use client'

import { useMemo, useState } from 'react'
import Link from 'next/link'
import { useParams, useRouter } from 'next/navigation'
import { Columns3, Info } from 'lucide-react'
import { isAdmin, useMe } from '@/features/auth/api'
import { useCreateComparison } from '@/features/comparisons/api'
import { useComponent, useComponentEvidence, useComponentStorybook, useRelatedComponents, useRelatedGuidelines, useRelatedTokens } from '@/features/components/api'
import { Button, EmptyState, ErrorState, ExtLink, fmtDate, KV, Missing, PageHeader, Panel, SearchInput, Select, Skeleton, Tabs, Tag, VerifyBadge } from '@/components/ui'
import { DataTable } from '@/components/ui/DataTable'
import s from '@/components/platform/page.module.scss'

type Tab = 'api' | 'keyboard' | 'a11y' | 'storybook' | 'structure' | 'evidence'

export default function ComponentDetailPage() {
  const id = Number(useParams<{ id: string }>().id)
  const router = useRouter()
  const { data: me } = useMe()
  const c = useComponent(id)
  const ev = useComponentEvidence(id)
  const rel = useRelatedComponents(id)
  const gls = useRelatedGuidelines(id)
  const toks = useRelatedTokens(id)
  const sb = useComponentStorybook(id)
  const createCmp = useCreateComparison()
  const [tab, setTab] = useState<Tab>('api')
  const [pq, setPq] = useState('')
  const [sub, setSub] = useState('')
  const d = c.data
  const props = useMemo(() => (d?.props ?? []).filter((p) => (!sub || p.subcomponent === sub) && (!pq || `${p.name} ${p.type} ${p.description}`.toLowerCase().includes(pq.toLowerCase()))), [d, pq, sub])
  if (c.error) return <ErrorState error={c.error} onRetry={() => c.refetch()} />
  const subs = Array.from(new Set((d?.props ?? []).map((p) => p.subcomponent ?? ''))).filter(Boolean)
  const peers = (rel.data ?? []).filter((x) => x.props_count > 0).slice(0, 3)

  return (
    <>
      <PageHeader
        crumbs={[{ href: '/components', label: 'Components' }]}
        title={d ? <>{d.name} <span className={s.muted} style={{ fontSize: '0.6em' }}>· {d.library}</span></> : <Skeleton w={260} h={30} />}
        description={d && <span className={s.row}><VerifyBadge status={d.verification_status} />{d.family && <Tag>{d.family}</Tag>}{d.kind && <Tag>{d.kind}</Tag>}{d.source_version && <Tag>v{d.source_version}</Tag>}<span className={s.mono}>{d.source_key}</span></span>}
        actions={d && isAdmin(me) && peers.length > 0 && (
          <Button icon={<Columns3 size={15} />} loading={createCmp.isPending}
            onClick={() => createCmp.mutate({ name: `${d.family ?? d.name}: ${d.library} vs ${peers.map((p) => p.library).join(', ')}`, kind: 'components', item_ids: [d.id, ...peers.map((p) => p.id)], dimensions: [] },
              { onSuccess: (r) => router.push(`/admin/comparisons/${r.data.id}`) })}>
            Compare with {peers.length} peer{peers.length > 1 ? 's' : ''}
          </Button>
        )}
      />
      {d && (
        <>
          <div className={s.notice}><Info size={16} aria-hidden /><span>{d.interpretation_note}</span></div>
          <div className={s.grid21}>
            <Panel title="Overview">
              <div className={s.pad}>
                {d.description ? <p style={{ marginBottom: 12 }}>{d.description}</p> : <Missing label="No description extracted" />}
                <KV items={[
                  ['Documentation', d.documentation_url && <ExtLink href={d.documentation_url} />],
                  ['Evidence source', <ExtLink key="e" href={d.source_url} />],
                  ['Detail level', d.detail_level], ['Frameworks', d.frameworks.join(', ')],
                  ['Subcomponents', d.subcomponents.length ? d.subcomponents.map((x) => x.name).join(', ') : null],
                  ['Variants (from source code)', d.variants ? <pre className={s.code}>{JSON.stringify(d.variants, null, 2)}</pre> : null],
                ]} />
                {d.notes.length > 0 && <ul style={{ marginTop: 10, paddingLeft: 18, color: 'var(--muted)', fontSize: '0.84rem' }}>{d.notes.map((n, i) => <li key={i}>{n}</li>)}</ul>}
              </div>
            </Panel>
            <div className={s.stack}>
              <Panel title={`Same family elsewhere (${rel.data?.length ?? 0})`}>
                <ul className={s.list}>
                  {rel.isLoading && <li><Skeleton h={60} /></li>}
                  {rel.data?.slice(0, 10).map((r) => (
                    <li key={r.id} className={s.row} style={{ justifyContent: 'space-between' }}>
                      <Link href={`/components/${r.id}`}>{r.name} <small className={s.muted}>· {r.library}</small></Link>
                      {r.props_count > 0 && <Tag>{r.props_count} props</Tag>}
                    </li>
                  ))}
                  {rel.data?.length === 0 && <li className={s.muted}>No same-family components with docs.</li>}
                </ul>
              </Panel>
              <Panel title={`Related guidelines (${gls.data?.length ?? 0})`}>
                <ul className={s.list}>
                  {gls.data?.slice(0, 8).map((g) => <li key={g.id}><Link href={`/admin/${g.record_type === 'pattern' ? 'patterns' : 'guidelines'}/${g.id}`}>{g.title}</Link></li>)}
                  {gls.data?.length === 0 && <li className={s.muted}>None matched by name/family.</li>}
                </ul>
              </Panel>
              {(toks.data?.length ?? 0) > 0 && (
                <Panel title={`Component tokens (${toks.data!.length})`}>
                  <ul className={s.list}>{toks.data!.slice(0, 10).map((t) => <li key={t.id} className={s.mono}><Link href={`/tokens?focus=${t.id}`}>{t.name}</Link> = {t.raw_value ?? '—'}</li>)}</ul>
                </Panel>
              )}
            </div>
          </div>

          <div style={{ margin: '18px 0 12px' }}>
            <Tabs<Tab> value={tab} onChange={setTab} tabs={[
              { value: 'api', label: 'Props / API', count: d.props.length },
              { value: 'storybook', label: 'Storybook & variants', count: (sb.data?.stories.length ?? 0) + (sb.data?.variants.length ?? 0) },
              { value: 'keyboard', label: 'Keyboard', count: d.keyboard.length },
              { value: 'a11y', label: 'Accessibility', count: d.accessibility_notes.length },
              { value: 'structure', label: 'Structure' },
              { value: 'evidence', label: 'Evidence', count: ev.data?.length },
            ]} />
          </div>
          <Panel>
            {tab === 'api' && (d.props.length === 0 ? <EmptyState title="No prop tables in the inspected documentation">{d.detail_level === 'index' ? 'This is a directory-level record; the official page was not parsed.' : 'Props may be documented in prose or passed through to an underlying primitive.'}</EmptyState> : (
              <>
                <div className={s.filters} style={{ padding: '12px 12px 0' }}>
                  <SearchInput value={pq} onChange={setPq} placeholder="Filter props…" delay={0} />
                  {subs.length > 1 && <Select label="Subcomponent" value={sub} onChange={setSub} options={[{ value: '', label: `All parts (${subs.length})` }, ...subs.map((x) => ({ value: x, label: x }))]} />}
                  <span className={s.filterMeta}>{props.length} props</span>
                </div>
                <DataTable caption="Props" rows={props.slice(0, 400)} rowKey={(p) => `${p.subcomponent}-${p.name}`}
                  columns={[
                    { key: 'sub', header: 'Part', cell: (p) => <span className={s.mono}>{p.subcomponent}</span>, width: '120px', hideBelow: 'md' },
                    { key: 'n', header: 'Prop', cell: (p) => <strong className={s.mono}>{p.name}</strong> },
                    { key: 't', header: 'Type', cell: (p) => <span className={s.mono} style={{ wordBreak: 'break-word' }}>{p.type ?? '—'}</span> },
                    { key: 'd', header: 'Default', cell: (p) => <span className={s.mono}>{p.default_value ?? '—'}</span>, hideBelow: 'md' },
                    { key: 'desc', header: 'Description', cell: (p) => p.description ?? <Missing />, hideBelow: 'lg' },
                  ]} />
              </>
            ))}
            {tab === 'storybook' && (
              sb.isLoading ? (
                <div className={s.pad}><Skeleton h={180} /></div>
              ) : (!sb.data?.stories?.length && !sb.data?.variants?.length) ? (
                <EmptyState title="No Storybook stories or variants for this component">
                  Storybook showcase extraction either did not match this component or no stories were discovered.
                </EmptyState>
              ) : (
                <>
                  {(sb.data.variants?.length ?? 0) > 0 && (
                    <>
                      <div style={{ padding: '16px 16px 4px' }}>
                        <h3 style={{ fontSize: '0.92rem', fontWeight: 600 }}>Extracted Component Variants ({sb.data.variants.length})</h3>
                      </div>
                      <DataTable
                        caption="Variants"
                        rows={sb.data.variants as Array<{ id: number; variant_name: string; property_name?: string; property_value?: string; variant_type?: string; story_id?: string }>}
                        rowKey={(v) => v.id}
                        columns={[
                          { key: 'n', header: 'Variant Name', cell: (v) => <strong className={s.mono}>{v.variant_name}</strong> },
                          { key: 'prop', header: 'Property', cell: (v) => <span className={s.mono}>{v.property_name ?? '—'}</span> },
                          { key: 'val', header: 'Value', cell: (v) => <span className={s.mono}>{v.property_value ?? '—'}</span> },
                          { key: 'type', header: 'Type', cell: (v) => <Tag>{v.variant_type ?? 'variant'}</Tag> },
                          { key: 'story', header: 'Story ID', cell: (v) => <span className={s.mono}>{v.story_id ?? '—'}</span>, hideBelow: 'md' },
                        ]}
                      />
                    </>
                  )}
                  {(sb.data.stories?.length ?? 0) > 0 && (
                    <>
                      <div style={{ padding: '16px 16px 4px' }}>
                        <h3 style={{ fontSize: '0.92rem', fontWeight: 600 }}>Linked Storybook Stories ({sb.data.stories.length})</h3>
                      </div>
                      <DataTable
                        caption="Stories"
                        rows={sb.data.stories as Array<{ id: number; name: string; title?: string; kind?: string; story_type?: string; tags?: string[]; docs_page_url?: string; iframe_url?: string }>}
                        rowKey={(st) => st.id}
                        columns={[
                          { key: 'title', header: 'Story / Kind', cell: (st) => <div><div className={s.mono}><strong>{st.name}</strong></div><div className={s.muted} style={{ fontSize: '0.8rem' }}>{st.title ?? st.kind}</div></div> },
                          { key: 'type', header: 'Type', cell: (st) => <Tag>{st.story_type ?? 'story'}</Tag>, width: '100px' },
                          { key: 'tags', header: 'Tags', cell: (st) => (st.tags || []).map((t) => <Tag key={t}>{t}</Tag>), hideBelow: 'md' },
                          { key: 'links', header: 'Links', cell: (st) => (
                            <div className={s.row}>
                              {st.docs_page_url && <ExtLink href={st.docs_page_url}>Docs</ExtLink>}
                              {st.iframe_url && <ExtLink href={st.iframe_url}>Iframe</ExtLink>}
                            </div>
                          ) },
                        ]}
                      />
                    </>
                  )}
                </>
              )
            )}
            {tab === 'keyboard' && (d.keyboard.length === 0 ? <EmptyState title="No keyboard table in the inspected documentation">Keyboard behaviour may still exist and be described in prose — check the evidence link.</EmptyState> : (
              <DataTable caption="Keyboard" rows={d.keyboard as { keys: string; description: string; section: string }[]} rowKey={(k) => `${k.section}-${k.keys}`}
                columns={[{ key: 'k', header: 'Keys', cell: (k) => <kbd className={s.mono}>{k.keys}</kbd>, width: '160px' }, { key: 'd', header: 'Behaviour', cell: (k) => k.description }, { key: 's', header: 'Section', cell: (k) => <span className={s.muted}>{k.section}</span>, hideBelow: 'md' }]} />
            ))}
            {tab === 'a11y' && (d.accessibility_notes.length === 0 ? <EmptyState title="No accessibility section extracted" /> : (
              <ul className={s.list}>{(d.accessibility_notes as { section: string; text: string }[]).map((a, i) => <li key={i}><strong style={{ fontWeight: 500 }}>{a.section}</strong><p className={s.muted} style={{ marginTop: 4 }}>{a.text}</p></li>)}</ul>
            ))}
            {tab === 'structure' && (
              <div className={s.pad}>
                <KV items={[
                  ['Anatomy', d.anatomy ? <pre className={s.code}>{d.anatomy}</pre> : null],
                  ['Data attributes', d.data_attributes.length ? <pre className={s.code}>{JSON.stringify(d.data_attributes.slice(0, 30), null, 2)}</pre> : null],
                  ['CSS variables', d.css_variables.length ? <pre className={s.code}>{JSON.stringify(d.css_variables.slice(0, 30), null, 2)}</pre> : null],
                  ['Examples documented', d.examples.length ? d.examples.slice(0, 30).join(' · ') : null],
                  ['Section outline', d.section_outline.length ? <pre className={s.code}>{d.section_outline.join('\n')}</pre> : null],
                ]} />
              </div>
            )}
            {tab === 'evidence' && (
              <DataTable caption="Evidence" loading={ev.isLoading} rows={ev.data} rowKey={(e) => e.id}
                columns={[
                  { key: 'u', header: 'Source URL', cell: (e) => <ExtLink href={e.url} /> },
                  { key: 'v', header: 'Version', cell: (e) => <span className={s.mono}>{e.source_version ?? '—'}</span>, hideBelow: 'md' },
                  { key: 'snap', header: 'Snapshot', cell: (e) => (e.raw_document_id ? <a className={s.mono} href={`/api/v1/documents/${e.raw_document_id}/content`}>#{e.raw_document_id}</a> : '—') },
                  { key: 'c', header: 'Captured', cell: (e) => fmtDate(e.captured_at), hideBelow: 'md' },
                ]} />
            )}
          </Panel>
        </>
      )}
    </>
  )
}
