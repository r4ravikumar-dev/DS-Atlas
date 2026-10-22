import type { Metadata } from 'next'
import Link from 'next/link'
import { notFound } from 'next/navigation'
import { ArrowDown } from 'lucide-react'
import { BackendError, getItem, getPage, optional } from '@/lib/api/server'
import { loadSystem } from '@/lib/api/systems'
import { previewKind, tokenValue } from '@/lib/tokens/preview'
import type { Token } from '@/lib/api/types'
import { TokenSwatch } from '@/components/tokens/TokenPreview'
import { Badge } from '@/components/kit/badge'
import { CopyButton } from '@/components/kit/copy-button'
import { ExternalLink } from '@/components/kit/external-link'
import { NotDocumented } from '@/components/kit/states'

type Params = { params: Promise<{ slug: string; token: string }> }
type TokenDetail = Token & { source_url: string | null; source_section: string | null; category?: string | null; tier?: string | null }

async function load(slug: string, ref: string) {
  const s = await loadSystem(slug)
  if (!/^[a-z0-9-]{1,220}$/i.test(ref)) notFound()
  try {
    return { s, t: await getItem<TokenDetail>(`/design-systems/${s.id}/tokens/${encodeURIComponent(ref)}`, { tags: [`system:${s.id}`, 'tokens'] }) }
  } catch (e) {
    if (e instanceof BackendError && e.status === 404) notFound()
    throw e
  }
}

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const { slug, token } = await params
  const { s, t } = await load(slug, token)
  return { title: `${t.path} — ${s.name}`, description: `${s.name} design token ${t.path}${t.raw_value ? ` (${t.raw_value})` : ''}. ${t.description ?? ''}`.trim().slice(0, 158), alternates: { canonical: `/systems/${s.slug}/tokens/${t.slug}` } }
}

/** One token within its own system. Alias references stay inside the system (the backend never resolves across systems). */
export default async function SystemToken({ params }: Params) {
  const { slug, token } = await params
  const { s, t } = await load(slug, token)
  const base = `/systems/${s.slug}`
  const [refs, deps] = await Promise.all([
    optional(getPage<Token>(`/tokens/${t.id}/references`, { tags: [`token:${t.id}`] })),
    optional(getPage<Token>(`/tokens/${t.id}/dependents`, { query: { page_size: 30 }, tags: [`token:${t.id}`] })),
  ])
  const href = (x: Token) => (x.system_slug && x.slug ? `/systems/${x.system_slug}/tokens/${x.slug}` : `/tokens/${x.id}`)
  return (
    <article className="grid gap-12 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
      <div className="flex flex-col gap-6">
        <nav aria-label="Breadcrumb" className="font-mono text-meta text-muted"><Link href={`${base}/tokens`} className="focus-ring hover:text-text">{s.name} tokens</Link>{t.category && <> / <Link href={`${base}/tokens?category=${t.category}`} className="focus-ring hover:text-text">{t.category}</Link></>}</nav>
        <div className="flex flex-wrap gap-1.5">{[...new Set([t.category, t.tier, t.theme, t.platform].filter(Boolean))].map((x) => <Badge key={x!}>{x}</Badge>)}</div>
        <h2 className="flex items-center gap-3 font-mono text-[clamp(1.3rem,1rem+1.6vw,2.2rem)] leading-tight font-medium tracking-tight break-all">{t.path}<CopyButton value={t.path} label="Copy token name" /></h2>
        {t.description ? <p className="measure text-text-2">{t.description}</p> : <NotDocumented>No description in the source.</NotDocumented>}
        <dl className="divide-y divide-line border-y border-line">
          {[
            ['Original value', t.raw_value ? <span key="r" className="flex items-center gap-1 font-mono">{t.raw_value}<CopyButton value={t.raw_value} label="Copy value" /></span> : <NotDocumented key="r">Not recorded in the source</NotDocumented>],
            ['Resolved value', t.resolved_value ? <span key="v" className="flex items-center gap-1 font-mono">{t.resolved_value}<CopyButton value={t.resolved_value} label="Copy value" /></span> : <span key="v" className="text-meta text-muted">{t.alias_of ? 'The alias could not be followed within this system' : 'Same as the original value'}</span>],
            ['Component', t.component ?? '—'],
            ['Source', t.source_url ? <span key="s"><ExternalLink href={t.source_url} className="font-mono text-[0.8rem] break-all" />{t.source_section && <span className="mt-1 block text-[0.75rem] text-muted">{t.source_section}</span>}</span> : '—'],
          ].map(([k, v]) => (
            <div key={k as string} className="grid gap-1 py-3.5 sm:grid-cols-[11rem_1fr]"><dt className="text-meta text-muted">{k}</dt><dd className="min-w-0 text-[0.92rem] break-words text-text">{v}</dd></div>
          ))}
        </dl>
      </div>
      <div className="flex flex-col gap-8">
        {previewKind(t) !== 'none' && (
          <div className="grid min-h-48 place-items-center rounded-md border border-line bg-surface/40 p-8">
            <TokenSwatch token={t} className="size-28" />
            <p className="mt-4 font-mono text-meta text-muted">{tokenValue(t)}</p>
          </div>
        )}
        <section aria-labelledby="chain">
          <h3 id="chain" className="eyebrow mb-4">Alias chain</h3>
          <ol className="flex flex-col items-start gap-1">
            <li className="rounded-xs border border-accent/40 bg-accent-soft px-3 py-2 font-mono text-[0.8rem] text-text">{t.path}</li>
            {refs?.data.length ? refs.data.map((r) => (
              <li key={r.id} className="flex flex-col items-start gap-1">
                <ArrowDown className="ml-3 size-4 text-faint" aria-label="references" />
                <Link href={href(r)} className="focus-ring flex items-center gap-2 rounded-xs border border-line px-3 py-2 font-mono text-[0.8rem] hover:border-line-strong"><TokenSwatch token={r} className="size-5" />{r.path}<span className="text-muted">= {r.raw_value ?? '—'}</span></Link>
              </li>
            )) : <li className="mt-2 text-meta text-muted">{t.alias_of ? `References ${t.alias_of}, which isn't among this system's collected tokens.` : 'Not an alias — this token holds its own value.'}</li>}
          </ol>
        </section>
        <section aria-labelledby="deps">
          <h3 id="deps" className="eyebrow mb-4">Tokens that reference this one{deps ? ` (${deps.meta.total_items})` : ''}</h3>
          {deps?.data.length ? (
            <ul className="flex flex-col divide-y divide-line border-y border-line">{deps.data.map((r) => <li key={r.id}><Link href={href(r)} className="focus-ring flex items-center gap-2 py-2 font-mono text-[0.78rem] hover:text-accent-text"><TokenSwatch token={r} className="size-5" />{r.path}</Link></li>)}</ul>
          ) : <p className="text-meta text-muted">None among this system&apos;s tokens.</p>}
        </section>
      </div>
    </article>
  )
}
