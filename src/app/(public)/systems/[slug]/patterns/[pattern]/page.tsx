import type { Metadata } from 'next'
import Link from 'next/link'
import { notFound } from 'next/navigation'
import { BackendError, getItem } from '@/lib/api/server'
import { loadSystem } from '@/lib/api/systems'
import { Markdown } from '@/components/ui/Markdown'
import { Badge } from '@/components/kit/badge'
import { ExternalLink } from '@/components/kit/external-link'
import { NotDocumented } from '@/components/kit/states'

type Params = { params: Promise<{ slug: string; pattern: string }> }
interface PatternDetail {
  id: number; slug: string; title: string; category_name: string; summary: string | null; section: string | null; kind: string | null; source_url: string
  content: Record<string, unknown>; evidence: { url: string }[]; mentioned_components: { id: number; name: string; slug: string; family: string | null }[]
}

async function load(slug: string, ref: string) {
  const s = await loadSystem(slug)
  if (!/^[a-z0-9-]{1,220}$/i.test(ref)) notFound()
  try {
    return { s, g: await getItem<PatternDetail>(`/design-systems/${s.id}/patterns/${encodeURIComponent(ref)}`, { tags: [`system:${s.id}`, 'guidelines'] }) }
  } catch (e) {
    if (e instanceof BackendError && e.status === 404) notFound()
    throw e
  }
}

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const { slug, pattern } = await params
  const { s, g } = await load(slug, pattern)
  return { title: `${g.title} — ${s.name}`, description: (g.summary ?? `${g.category_name} guidance from ${s.name}.`).slice(0, 158), alternates: { canonical: `/systems/${s.slug}/patterns/${g.slug}` } }
}

export default async function SystemPattern({ params }: Params) {
  const { slug, pattern } = await params
  const { s, g } = await load(slug, pattern)
  const base = `/systems/${s.slug}`
  const body = typeof g.content?.body === 'string' ? g.content.body : typeof g.content?.text === 'string' ? g.content.text : null
  const sources = [...new Set([g.source_url, ...g.evidence.map((e) => e.url)].filter(Boolean))]
  return (
    <article className="grid gap-12 lg:grid-cols-[minmax(0,1fr)_18rem]">
      <div className="flex min-w-0 flex-col gap-6">
        <nav aria-label="Breadcrumb" className="font-mono text-meta text-muted"><Link href={`${base}/patterns`} className="focus-ring hover:text-text">{s.name} patterns</Link> / {g.category_name}</nav>
        <h2 className="text-section font-medium">{g.title}</h2>
        <div className="flex flex-wrap gap-1.5"><Badge tone="accent">{g.category_name}</Badge>{g.section && <Badge>{g.section}</Badge>}</div>
        {g.summary ? <p className="measure text-lg leading-relaxed text-text-2">{g.summary}</p> : !body && <NotDocumented>Only the link to this page was collected — read it on the official site.</NotDocumented>}
        {body && <div className="measure"><Markdown>{body.slice(0, 20000)}</Markdown></div>}
      </div>
      <aside className="flex flex-col gap-8 lg:sticky lg:top-[calc(var(--header-h)+4.5rem)] lg:self-start">
        {g.mentioned_components.length > 0 && (
          <section aria-labelledby="mc">
            <h3 id="mc" className="eyebrow mb-3">{s.name} components mentioned</h3>
            <ul className="flex flex-wrap gap-1.5">{g.mentioned_components.map((c) => <li key={c.id}><Link href={`${base}/components/${c.slug}`} className="focus-ring inline-flex rounded-xs border border-line-strong px-2 py-1 text-meta hover:border-text/40">{c.name}</Link></li>)}</ul>
            <p className="mt-2 text-[0.7rem] text-muted">Matched by name in the guidance text.</p>
          </section>
        )}
        <section aria-labelledby="src">
          <h3 id="src" className="eyebrow mb-3">Official source</h3>
          <ul className="flex flex-col gap-2">{sources.map((u) => <li key={u}><ExternalLink href={u} className="font-mono text-[0.78rem] break-all" /></li>)}</ul>
        </section>
      </aside>
    </article>
  )
}
