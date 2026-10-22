import Link from 'next/link'
import { ArrowUpRight } from 'lucide-react'
import type { System } from '@/lib/api/types'
import { cn } from '@/lib/cn'
import { Lift } from '../motion/Lift'
import { SystemLogo } from '../system/SystemLogo'
import { ResourceIndicators } from './ResourceIndicators'

type CardSystem = Pick<System, 'id' | 'name' | 'organization' | 'description' | 'frameworks' | 'links' | 'component_count' | 'token_count'> & { slug?: string | null; logo?: { url: string; alt?: string | null } | null }

/** Directory card. The whole card is clickable through a stretched title link (one tab stop, no nested links). */
export function SystemCard({ system: s, index, variant = 'grid' }: { system: CardSystem; index?: number; variant?: 'grid' | 'list' }) {
  const href = `/systems/${s.slug ?? s.id}`
  const tech = s.frameworks.flatMap((f) => f.split(/\s+/)).filter((v, i, a) => a.indexOf(v) === i).slice(0, 4)
  if (variant === 'list') {
    return (
      <article className="group relative grid grid-cols-[auto_1fr] items-center gap-x-5 gap-y-3 border-b border-line py-5 transition-colors hover:bg-surface/50 md:grid-cols-[3rem_auto_minmax(0,1.3fr)_minmax(0,1fr)_auto] md:px-2">
        {index !== undefined && <span className="hidden font-mono text-meta text-faint md:block">{String(index).padStart(3, '0')}</span>}
        <SystemLogo name={s.name} logo={s.logo} size="sm" />
        <div className="min-w-0">
          <h3 className="truncate text-card font-medium">
            <Link href={href} className="focus-ring after:absolute after:inset-0">{s.name}</Link>
          </h3>
          <p className="truncate text-meta text-muted">{s.organization ?? 'Organisation not recorded'}</p>
        </div>
        <ResourceIndicators links={s.links} className="col-span-2 md:col-span-1" />
        <div className="col-span-2 flex items-center gap-4 font-mono text-meta text-muted md:col-span-1 md:justify-end">
          <span>{s.component_count} components</span><span>{s.token_count} tokens</span>
        </div>
      </article>
    )
  }
  return (
    <Lift className="h-full">
      <article className="group relative flex h-full flex-col gap-5 rounded-sm border border-line bg-surface/40 p-5 transition-[border-color,background-color] duration-300 hover:border-line-strong hover:bg-surface">
        <header className="flex items-start gap-4">
          <SystemLogo name={s.name} logo={s.logo} />
          <div className="min-w-0 flex-1">
            <h3 className="text-card font-medium">
              <Link href={href} className="focus-ring after:absolute after:inset-0">{s.name}</Link>
            </h3>
            <p className="truncate text-meta text-muted">{s.organization ?? 'Organisation not recorded'}</p>
          </div>
          <ArrowUpRight className="size-4 shrink-0 text-faint transition-[color,transform] duration-300 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 group-hover:text-accent-text" aria-hidden />
        </header>
        <p className={cn('line-clamp-3 text-[0.92rem] leading-relaxed', s.description ? 'text-text-2' : 'text-faint italic')}>
          {s.description ?? 'No description collected yet.'}
        </p>
        {tech.length > 0 && (
          <ul className="flex flex-wrap gap-1.5" aria-label="Technologies">
            {tech.map((t) => <li key={t} className="rounded-xs bg-surface-2 px-1.5 py-0.5 font-mono text-[0.68rem] text-text-2">{t}</li>)}
          </ul>
        )}
        <div className="mt-auto flex flex-col gap-3 border-t border-line pt-4">
          <ResourceIndicators links={s.links} />
          <p className="font-mono text-[0.7rem] text-muted">{s.component_count.toLocaleString()} components · {s.token_count.toLocaleString()} tokens</p>
        </div>
      </article>
    </Lift>
  )
}
