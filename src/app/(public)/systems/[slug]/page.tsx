import type { Metadata } from 'next'
import Link from 'next/link'
import { ArrowRight, MousePointerClick } from 'lucide-react'
import { getItem, getPage, optional } from '@/lib/api/server'
import { fmtDate } from '@/lib/api/public'
import { loadSystem, systemOrRedirect } from '@/lib/api/systems'
import { isColor, tokenValue } from '@/lib/tokens/preview'
import type { Component, Token } from '@/lib/api/types'
import { ComponentCard } from '@/components/catalog/ComponentCard'
import { NotDocumented } from '@/components/kit/states'
import { Stagger, StaggerItem } from '@/components/motion/Reveal'

type Params = { params: Promise<{ slug: string }> }
interface FamilyGroup { name: string; description?: string; count: number; families: { name: string; slug: string; count: number; with_playground: number }[] }

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const s = await loadSystem((await params).slug)
  const description = (s.description ?? `${s.name}${s.organization ? ` by ${s.organization}` : ''}: components, design tokens, patterns and official resources.`).slice(0, 158)
  return {
    title: s.organization ? `${s.name} — ${s.organization}` : s.name, description, alternates: { canonical: `/systems/${s.slug}` },
    openGraph: { title: s.name, description, url: `/systems/${s.slug}`, type: 'article' },
  }
}

export default async function SystemOverview({ params }: Params) {
  const s = await systemOrRedirect((await params).slug)
  const [families, playgrounds, colors] = await Promise.all([
    optional(getItem<FamilyGroup[]>(`/design-systems/${s.id}/component-families`, { tags: [`system:${s.id}`] })),
    optional(getPage<Component>(`/design-systems/${s.id}/playgrounds`, { query: { page_size: 6 }, tags: [`system:${s.id}`] })),
    optional(getPage<Token>(`/design-systems/${s.id}/tokens`, { query: { category: 'color', page_size: 24 }, tags: [`system:${s.id}`] })),
  ])
  const base = `/systems/${s.slug}`
  const swatches = (colors?.data ?? []).filter((t) => isColor(tokenValue(t))).slice(0, 16)
  const aliases = s.aliases.filter((a) => a.toLowerCase() !== s.name.toLowerCase())
  const facts = [
    ['Styling approach', s.styling_strategy], ['Token architecture', s.token_architecture], ['Accessibility documentation', s.accessibility_documentation],
    ['Governance', s.governance], ['Also known as', aliases.length ? aliases.join(', ') : null],
  ].filter(([, v]) => v) as [string, string][]

  return (
    <div className="flex flex-col gap-20">
      <section className="grid gap-10 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]" aria-labelledby="about-title">
        <div className="flex flex-col gap-6">
          <h2 id="about-title" className="sr-only">About {s.name}</h2>
          {s.description ? <p className="measure text-xl leading-relaxed text-text-2">{s.description}</p> : <NotDocumented>No description collected yet.</NotDocumented>}
          {facts.length > 0 && (
            <dl className="divide-y divide-line border-y border-line">
              {facts.map(([k, v]) => (
                <div key={k} className="grid gap-1 py-3.5 sm:grid-cols-[13rem_1fr]"><dt className="text-meta text-muted">{k}</dt><dd className="text-[0.95rem] text-text">{v}</dd></div>
              ))}
            </dl>
          )}
          <p className="font-mono text-[0.72rem] text-muted">
            Listed by {s.source_count} independent {s.source_count === 1 ? 'source' : 'sources'}{s.content_updated_at ? ` · updated ${fmtDate(s.content_updated_at)}` : ''}
          </p>
        </div>
        {s.cover ? (
          <figure className="flex flex-col gap-2">
            <div className="overflow-hidden rounded-md border border-line bg-surface" style={{ aspectRatio: s.cover.width && s.cover.height ? `${s.cover.width} / ${s.cover.height}` : '1200 / 630' }}>
              {/* eslint-disable-next-line @next/next/no-img-element -- the owner's published image, referenced at its original URL */}
              <img src={s.cover.url} alt={s.cover.alt ?? `Preview image published by ${s.name}`} width={s.cover.width ?? 1200} height={s.cover.height ?? 630}
                loading="lazy" decoding="async" referrerPolicy="no-referrer" className="size-full object-cover" />
            </div>
            <figcaption className="text-[0.72rem] text-muted">
              Image published by {s.organization ?? s.cover.source_host} on <a href={s.cover.page_url ?? '#'} target="_blank" rel="noopener noreferrer nofollow" className="focus-ring underline underline-offset-2">{s.cover.source_host}</a>. Shown for reference; rights remain with the owner.
            </figcaption>
          </figure>
        ) : swatches.length > 0 ? (
          <div aria-label={`${s.name} colour tokens`} className="grid grid-cols-4 gap-2 self-start">
            {swatches.map((t) => <Link key={t.id} href={`${base}/tokens/${t.slug}`} title={`${t.path}: ${tokenValue(t)}`} className="focus-ring aspect-square rounded-sm border border-line" style={{ background: tokenValue(t) }}><span className="sr-only">{t.path}</span></Link>)}
          </div>
        ) : null}
      </section>

      {families && families.length > 0 && (
        <section aria-labelledby="fam-title">
          <div className="mb-8 flex flex-wrap items-baseline justify-between gap-4">
            <h2 id="fam-title" className="text-section font-medium">Component families</h2>
            <Link href={`${base}/components`} className="focus-ring inline-flex items-center gap-1 text-meta text-accent-text underline decoration-accent/40 underline-offset-4">All {s.component_count} components <ArrowRight className="size-3.5" aria-hidden /></Link>
          </div>
          <ul className="grid gap-px overflow-hidden rounded-sm border border-line bg-line sm:grid-cols-2 lg:grid-cols-3">
            {families.map((g) => (
              <li key={g.name} className="flex flex-col gap-3 bg-bg p-5">
                <p className="flex items-baseline justify-between gap-3"><span className="text-card font-medium">{g.name}</span><span className="font-mono text-meta text-muted">{g.count}</span></p>
                <ul className="flex flex-wrap gap-1.5">
                  {g.families.map((f) => (
                    <li key={f.slug}><Link href={`${base}/components?family=${encodeURIComponent(f.name)}`} className="focus-ring inline-flex items-center gap-1.5 rounded-xs border border-line-strong px-2 py-1 text-meta text-text-2 hover:border-text/40 hover:text-text">{f.name}<span className="font-mono text-[0.66rem] text-faint">{f.count}</span></Link></li>
                  ))}
                </ul>
              </li>
            ))}
          </ul>
        </section>
      )}

      {playgrounds && playgrounds.data.length > 0 && (
        <section aria-labelledby="pg-title">
          <div className="mb-8 flex flex-wrap items-baseline justify-between gap-4">
            <h2 id="pg-title" className="flex items-center gap-2 text-section font-medium"><MousePointerClick className="size-6 text-accent-text" aria-hidden />Try it live</h2>
            <Link href={`${base}/playground`} className="focus-ring inline-flex items-center gap-1 text-meta text-accent-text underline decoration-accent/40 underline-offset-4">{playgrounds.meta.total_items} interactive previews <ArrowRight className="size-3.5" aria-hidden /></Link>
          </div>
          <Stagger as="ul" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {playgrounds.data.map((c) => <StaggerItem as="li" key={c.id}><ComponentCard c={c} showSystem={false} /></StaggerItem>)}
          </Stagger>
        </section>
      )}
    </div>
  )
}
