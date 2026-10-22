import Link from 'next/link'
import { notFound, permanentRedirect } from 'next/navigation'
import { BackendError, getItem } from '@/lib/api/server'
import { Markdown } from '../ui/Markdown'
import { Badge } from '../kit/badge'
import { ExternalLink } from '../kit/external-link'
import { NotDocumented } from '../kit/states'

interface Detail { id: number; slug: string | null; system_slug: string | null; title: string; category_name: string; kind: string | null; summary: string | null; section: string | null; design_system_name: string | null; source_url: string; content: Record<string, unknown>; evidence: { url: string }[] }

export async function loadResearch(kind: 'patterns' | 'guidelines', id: string): Promise<Detail> {
  if (!/^\d{1,9}$/.test(id)) notFound()
  let g: Detail
  try {
    g = await getItem<Detail>(`/${kind}/${id}`, { tags: ['guidelines'] })
  } catch (e) {
    if (e instanceof BackendError && e.status === 404) notFound()
    throw e
  }
  // guidance owned by one design system lives inside that system's workspace
  if (g.system_slug && g.slug) permanentRedirect(`/systems/${g.system_slug}/patterns/${g.slug}`)
  return g
}

/** Cross-system research guidance (checklists, specifications, overviews) — not owned by any single design system. */
export function ResearchDetail({ g }: { g: Detail }) {
  const body = typeof g.content?.body === 'string' ? g.content.body : typeof g.content?.text === 'string' ? g.content.text : null
  const sources = [...new Set([g.source_url, ...g.evidence.map((e) => e.url)].filter(Boolean))]
  return (
    <article className="container-page grid gap-12 pt-12 lg:grid-cols-[minmax(0,1fr)_18rem]">
      <div className="flex min-w-0 flex-col gap-6">
        <nav aria-label="Breadcrumb" className="font-mono text-meta text-muted"><Link href="/patterns" className="focus-ring hover:text-text">Pattern library</Link> / Cross-system research</nav>
        <h1 className="text-title font-medium">{g.title}</h1>
        <div className="flex flex-wrap gap-1.5"><Badge tone="accent">{g.category_name}</Badge>{g.kind && <Badge>{g.kind.replace(/_/g, ' ')}</Badge>}{g.section && <Badge>{g.section}</Badge>}</div>
        {g.summary ? <p className="measure text-lg leading-relaxed text-text-2">{g.summary}</p> : !body && <NotDocumented>Only the link to this page was collected — read it at the source.</NotDocumented>}
        {body && <div className="measure"><Markdown>{body.slice(0, 20000)}</Markdown></div>}
        <p className="text-[0.75rem] text-muted">Cross-system research: this guidance comes from a specification, checklist or directory, not from one design system&apos;s documentation.</p>
      </div>
      <aside className="flex flex-col gap-3 lg:sticky lg:top-[calc(var(--header-h)+2rem)] lg:self-start">
        <p className="eyebrow">Source</p>
        <ul className="flex flex-col gap-2">{sources.map((u) => <li key={u}><ExternalLink href={u} className="font-mono text-[0.78rem] break-all" /></li>)}</ul>
      </aside>
    </article>
  )
}
