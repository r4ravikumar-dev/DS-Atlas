import type { Metadata } from 'next'
import Link from 'next/link'
import { notFound } from 'next/navigation'
import { ArrowRight, BookOpen, Columns3, MousePointerClick } from 'lucide-react'
import { BackendError, getItem, getPage, optional } from '@/lib/api/server'
import { loadSystem } from '@/lib/api/systems'
import { propsSignature, variantAxes } from '@/lib/components/axes'
import type { Component, ComponentDetail, Guideline, StorybookStory, Token } from '@/lib/api/types'
import { componentHref } from '@/components/catalog/ComponentCard'
import { PropsExplorer } from '@/components/details/PropsExplorer'
import { SectionIndex } from '@/components/details/SectionIndex'
import { Section } from '@/components/details/Section'
import { AdminShortcut } from '@/components/details/AdminShortcut'
import { TokenSwatch } from '@/components/tokens/TokenPreview'
import { Badge } from '@/components/kit/badge'
import { Button } from '@/components/kit/button'
import { CodeBlock } from '@/components/kit/code-block'
import { ExternalLink } from '@/components/kit/external-link'
import { InlineText } from '@/components/kit/inline-text'
import { EmptyState, NotDocumented } from '@/components/kit/states'

type Params = { params: Promise<{ slug: string; component: string }> }
type Detail = ComponentDetail & { slug: string; system_slug: string; system_name: string; family_category: string; playground: 'live' | 'adapter' | 'docs' }
interface Evidence { id: number; url: string; source_section: string | null; source_version: string | null }

async function load(slug: string, ref: string) {
  const s = await loadSystem(slug)
  if (!/^[a-z0-9-]{1,160}$/i.test(ref)) notFound()
  try {
    const c = await getItem<Detail>(`/design-systems/${s.id}/components/${encodeURIComponent(ref)}`, { tags: [`system:${s.id}`, 'components'] })
    return { s, c }
  } catch (e) {
    if (e instanceof BackendError && e.status === 404) notFound()
    throw e
  }
}

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const { slug, component } = await params
  const { s, c } = await load(slug, component)
  const description = (c.description ?? `${c.name} from ${s.name}: props, variants, keyboard behaviour and accessibility notes.`).slice(0, 158)
  return { title: `${c.name} — ${s.name}`, description, alternates: { canonical: `/systems/${s.slug}/components/${c.slug}` }, openGraph: { title: `${c.name} — ${s.name}`, description, type: 'article' } }
}

export default async function SystemComponent({ params }: Params) {
  const { slug, component } = await params
  const { s, c } = await load(slug, component)
  const base = `/systems/${s.slug}`
  const [related, tokens, guides, sb, sources] = await Promise.all([
    optional(getItem<Component[]>(`/components/${c.id}/related-components`, { query: { limit: 8 }, tags: [`component:${c.id}`] })),
    optional(getPage<Token>(`/components/${c.id}/related-tokens`, { query: { limit: 12 }, tags: [`component:${c.id}`] })),
    optional(getPage<Guideline>(`/components/${c.id}/related-guidelines`, { query: { limit: 6 }, tags: [`component:${c.id}`] })),
    optional(getItem<{ stories: StorybookStory[] }>(`/components/${c.id}/storybook`, { tags: [`component:${c.id}`] })),
    optional(getPage<Evidence>(`/components/${c.id}/evidence`, { tags: [`component:${c.id}`] })),
  ])
  const axes = variantAxes(c.props)
  const signature = propsSignature(c.name, c.props)
  const keyboard = c.keyboard as { keys: string; description: string }[]
  const a11y = c.accessibility_notes as { text: string; section?: string }[]
  const peers = (related ?? []).filter((r) => r.props_count > 0).slice(0, 3) as (Component & { system_name?: string })[]
  const sections = [
    { id: 'api', label: 'Properties & API', count: c.props.length },
    { id: 'variants', label: 'Variants & examples' },
    { id: 'interaction', label: 'Interaction', count: keyboard.length || undefined },
    { id: 'accessibility', label: 'Accessibility', count: a11y.length || undefined },
    { id: 'related', label: 'Related' },
    { id: 'sources', label: 'Sources' },
  ]

  return (
    <article className="flex flex-col gap-12">
      <header className="grid gap-8 border-b border-line pb-10 lg:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
        <div className="flex flex-col gap-5">
          <nav aria-label="Breadcrumb" className="font-mono text-meta text-muted">
            <ol className="flex flex-wrap items-center gap-2"><li><Link href={`${base}/components`} className="focus-ring hover:text-text">{s.name} components</Link></li>{c.family && <><li aria-hidden>/</li><li><Link href={`${base}/components?family=${encodeURIComponent(c.family)}`} className="focus-ring hover:text-text">{c.family}</Link></li></>}</ol>
          </nav>
          <h2 className="text-title font-medium">{c.name}</h2>
          <div className="flex flex-wrap items-center gap-2">
            {c.family && <Badge tone="accent">{c.family}</Badge>}
            {c.library && c.library !== s.name && <Badge>{c.library}</Badge>}
            {c.frameworks.map((f) => <Badge key={f}>{f}</Badge>)}
            {c.source_version && <span className="font-mono text-meta text-muted">v{c.source_version}</span>}
          </div>
          {c.description ? <p className="measure text-lg leading-relaxed text-text-2">{c.description}</p> : <NotDocumented>No description in the collected documentation.</NotDocumented>}
          <div className="flex flex-wrap items-center gap-3">
            {c.playground !== 'docs' && <Button asChild variant="primary"><Link href={`${base}/components/${c.slug}/playground`}><MousePointerClick className="size-4" aria-hidden />Open playground</Link></Button>}
            {c.documentation_url && <Button asChild variant={c.playground === 'docs' ? 'primary' : 'secondary'}><a href={c.documentation_url} target="_blank" rel="noopener noreferrer nofollow"><BookOpen className="size-4" aria-hidden />Official documentation<span className="sr-only">(opens in a new tab)</span></a></Button>}
            {peers.length > 0 && (
              <Button asChild variant="ghost">
                <Link href={`/compare?kind=components&ids=${[c.id, ...peers.map((p) => p.id)].join(',')}&labels=${encodeURIComponent([`${c.name} (${s.name})`, ...peers.map((p) => `${p.name} (${p.system_name ?? p.library})`)].map((l) => l.replace(/\|/g, ' ')).join('|'))}`}>
                  <Columns3 className="size-4" aria-hidden />Compare with other systems
                </Link>
              </Button>
            )}
            <AdminShortcut href={`/admin/components/${c.id}`} />
          </div>
        </div>
        <dl className="grid h-fit grid-cols-2 gap-px overflow-hidden rounded-sm border border-line bg-line text-meta">
          {[['Design system', s.name], ['Family', c.family ?? '—'], ['Documented props', c.props_count.toLocaleString()], ['Parts', (c.subcomponents?.length || 1).toLocaleString()],
            ['Keyboard rows', c.keyboard_count.toLocaleString()], ['Preview', c.playground === 'live' ? 'Live component' : c.playground === 'adapter' ? 'Platform preview' : 'Documentation only']].map(([k, v]) => (
            <div key={k} className="bg-bg p-4"><dt className="eyebrow mb-1.5">{k}</dt><dd className="text-text">{v}</dd></div>
          ))}
        </dl>
      </header>

      <div className="grid gap-10 lg:grid-cols-[13rem_minmax(0,1fr)] lg:gap-16">
        <div className="contents lg:block"><SectionIndex sections={sections} /></div>
        <div className="flex min-w-0 flex-col gap-20">
          <Section id="api" title="Properties & API" count={c.props.length}>
            {c.props.length === 0 ? <EmptyState title="No prop tables in the collected documentation" backToSite={false}>Props may be described in prose on the official page.</EmptyState> : (
              <div className="flex flex-col gap-8">
                <PropsExplorer props={c.props} />
                {signature && <CodeBlock code={signature} label="Generated from the documented API — not copied from source" />}
              </div>
            )}
          </Section>

          <Section id="variants" title="Variants & examples">
            <div className="flex flex-col gap-10">
              {axes.length > 0 ? (
                <div>
                  <p className="eyebrow mb-4">Documented values</p>
                  <ul className="flex flex-col gap-4">
                    {axes.map((a) => (
                      <li key={a.name} className="grid gap-2 md:grid-cols-[10rem_1fr]">
                        <span className="font-mono text-meta text-text">{a.name}</span>
                        <ul className="flex flex-wrap gap-1.5">{a.values.map((v) => <li key={v}><Badge tone={v === a.default ? 'accent' : 'neutral'}>{v}{v === a.default ? ' · default' : ''}</Badge></li>)}</ul>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : <p className="text-meta text-muted">The documented API doesn&apos;t enumerate variant or size values.</p>}
              {sb && sb.stories.length > 0 && (
                <div>
                  <p className="eyebrow mb-4">Storybook stories</p>
                  <ul className="divide-y divide-line border-y border-line">
                    {sb.stories.slice(0, 20).map((st) => (
                      <li key={st.id} className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 py-3">
                        <span><span className="text-text">{st.name}</span> <span className="font-mono text-[0.72rem] text-muted">{st.title}</span></span>
                        <ExternalLink href={st.story_url} className="text-meta">Open story</ExternalLink>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {c.examples.length > 0 && (
                <div>
                  <p className="eyebrow mb-3">Examples on the official page</p>
                  <ul className="flex flex-wrap gap-1.5">{[...new Set(c.examples)].slice(0, 30).map((e) => <li key={e}><Badge tone="muted">{e}</Badge></li>)}</ul>
                </div>
              )}
            </div>
          </Section>

          <Section id="interaction" title="Interaction" count={keyboard.length || undefined}>
            {keyboard.length === 0 ? <p className="text-meta text-muted">No keyboard table in the collected documentation.</p> : (
              <ul className="divide-y divide-line border-y border-line">
                {keyboard.map((k, i) => (
                  <li key={i} className="grid gap-2 py-3.5 md:grid-cols-[10rem_1fr]">
                    <span className="flex flex-wrap gap-1">{k.keys.split(/\s*\+\s*/).map((key, j) => <kbd key={j} className="rounded-xs border border-b-2 border-line-strong bg-surface px-1.5 py-0.5 font-mono text-[0.72rem] text-text">{key}</kbd>)}</span>
                    <span className="text-[0.92rem] text-text-2"><InlineText text={k.description} /></span>
                  </li>
                ))}
              </ul>
            )}
          </Section>

          <Section id="accessibility" title="Accessibility" count={a11y.length || undefined}>
            {a11y.length === 0 ? <p className="text-meta text-muted">No accessibility section in the collected documentation.</p> : (
              <ul className="flex flex-col gap-5">
                {a11y.map((a, i) => (
                  <li key={i} className="border-l-2 border-accent/50 pl-4">
                    {a.section && <p className="eyebrow mb-1.5">{a.section}</p>}
                    <p className="measure text-[0.95rem] leading-relaxed text-text-2"><InlineText text={a.text} /></p>
                  </li>
                ))}
              </ul>
            )}
          </Section>

          <Section id="related" title="Related">
            <div className="grid gap-10 xl:grid-cols-3">
              <div>
                <p className="eyebrow mb-3">{s.name} tokens</p>
                {tokens?.data.length ? (
                  <ul className="flex flex-col divide-y divide-line border-y border-line">
                    {tokens.data.map((t) => <li key={t.id}><Link href={`${base}/tokens/${t.slug ?? t.id}`} className="focus-ring flex items-center gap-3 py-2 font-mono text-[0.75rem] hover:text-accent-text"><TokenSwatch token={t} className="size-5" /><span className="truncate">{t.path}</span></Link></li>)}
                  </ul>
                ) : <p className="text-meta text-muted">No component-scoped tokens recorded.</p>}
              </div>
              <div>
                <p className="eyebrow mb-3">Guidance</p>
                {guides?.data.length ? (
                  <ul className="flex flex-col divide-y divide-line border-y border-line">
                    {guides.data.map((g) => <li key={g.id}><Link href={g.system_slug && g.slug ? `/systems/${g.system_slug}/patterns/${g.slug}` : `/patterns/${g.id}`} className="focus-ring block py-2.5 text-[0.9rem] hover:text-accent-text"><span className="block truncate">{g.title}</span>{g.design_system_name && <span className="text-[0.72rem] text-muted">{g.design_system_name}</span>}</Link></li>)}
                  </ul>
                ) : <p className="text-meta text-muted">None found.</p>}
              </div>
              <div>
                <p className="eyebrow mb-3">Same family in other systems</p>
                {related?.length ? (
                  <ul className="flex flex-col divide-y divide-line border-y border-line">
                    {(related as (Component & { system_name?: string })[]).map((r) => (
                      <li key={r.id}><Link href={componentHref(r)} className="focus-ring group flex items-center justify-between gap-3 py-2.5 hover:text-accent-text"><span className="min-w-0 truncate">{r.name} <span className="text-meta text-muted">· {r.system_name ?? r.library}</span></span><ArrowRight className="size-3.5 shrink-0 text-faint" aria-hidden /></Link></li>
                    ))}
                  </ul>
                ) : <p className="text-meta text-muted">None found.</p>}
                <p className="mt-3 text-[0.72rem] text-muted">Each is a separate implementation with its own API — open one to see its props.</p>
              </div>
            </div>
          </Section>

          <Section id="sources" title="Sources">
            <ul className="flex flex-col gap-2">
              {c.documentation_url && <li><ExternalLink href={c.documentation_url} className="font-mono text-[0.8rem] break-all">{c.documentation_url}</ExternalLink></li>}
              {(sources?.data ?? []).filter((e) => e.url !== c.documentation_url).map((e) => (
                <li key={e.id}><ExternalLink href={e.url} className="font-mono text-[0.8rem] break-all" />{e.source_section && <span className="ml-2 text-[0.72rem] text-muted">{e.source_section}</span>}</li>
              ))}
            </ul>
          </Section>
        </div>
      </div>
    </article>
  )
}
