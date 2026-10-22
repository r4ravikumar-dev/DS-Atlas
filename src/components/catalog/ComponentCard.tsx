import Link from 'next/link'
import { Accessibility, Keyboard, MousePointerClick } from 'lucide-react'
import type { Component } from '@/lib/api/types'
import { Lift } from '../motion/Lift'

export const DETAIL_LEVEL: Record<string, { label: string; hint: string }> = {
  api: { label: 'Structured API', hint: 'Props, keyboard tables and accessibility notes parsed from official docs' },
  doc: { label: 'Docs page', hint: 'An official documentation page was read' },
  index: { label: 'Directory link', hint: 'Only proves the system documents this component at a URL' },
  editorial_highlight: { label: 'Editorial note', hint: 'Mentioned in a curated directory' },
}

/** Component card — always names its library, so a Button from one library is never mistaken for another's. */
export const componentHref = (c: { id: number; slug?: string | null; system_slug?: string | null }) =>
  c.system_slug && c.slug ? `/systems/${c.system_slug}/components/${c.slug}` : `/components/${c.id}`

type CardComponent = Pick<Component, 'id' | 'name' | 'library' | 'description' | 'family' | 'props_count' | 'keyboard_count' | 'a11y_count' | 'frameworks'> &
  { slug?: string | null; system_slug?: string | null; system_name?: string | null; playground?: string | null }

export function ComponentCard({ c, showSystem = true }: { c: CardComponent; showSystem?: boolean }) {
  return (
    <Lift className="h-full">
      <article className="group relative flex h-full flex-col gap-3 rounded-sm border border-line bg-surface/40 p-4 transition-colors hover:border-line-strong hover:bg-surface">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 className="truncate text-card font-medium"><Link href={componentHref(c)} className="focus-ring after:absolute after:inset-0">{c.name}</Link></h3>
            {showSystem && <p className="truncate text-meta text-muted">{c.system_name ?? c.library}{c.library && c.system_name && c.library !== c.system_name ? ` · ${c.library}` : ''}</p>}
          </div>
          {c.playground && c.playground !== 'docs' && (
            <span className="inline-flex shrink-0 items-center gap-1 text-[0.7rem] text-accent-text" title="Has an interactive preview"><MousePointerClick className="size-3.5" aria-hidden />Preview</span>
          )}
        </div>
        {c.description && <p className="line-clamp-2 text-[0.88rem] text-text-2">{c.description}</p>}
        <div className="mt-auto flex flex-wrap items-center gap-x-3 gap-y-1.5 pt-2 font-mono text-[0.7rem] text-muted">
          {c.family && <span className="text-text-2">{c.family}</span>}
          {c.props_count > 0 && <span>{c.props_count.toLocaleString()} props</span>}
          {c.keyboard_count > 0 && <span className="inline-flex items-center gap-1"><Keyboard className="size-3" aria-hidden />{c.keyboard_count} keys</span>}
          {c.a11y_count > 0 && <span className="inline-flex items-center gap-1"><Accessibility className="size-3" aria-hidden />a11y notes</span>}
          {c.frameworks.slice(0, 2).map((f) => <span key={f}>{f}</span>)}
        </div>
      </article>
    </Lift>
  )
}
