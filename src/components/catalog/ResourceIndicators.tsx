import type { ResourceLink } from '@/lib/api/types'
import { cn } from '@/lib/cn'
import { PRIMARY_RESOURCES, RESOURCE_META } from './resources'

/** The official resources a system publishes. Only resources that exist are shown — nothing is flagged as missing. */
export function ResourceIndicators({ links, className }: { links: Pick<ResourceLink, 'type' | 'url'>[]; className?: string }) {
  const present = PRIMARY_RESOURCES.filter((t) => links.some((l) => l.type === t))
  if (present.length === 0) return null
  return (
    <ul className={cn('flex flex-wrap gap-1.5', className)} aria-label="Official resources">
      {present.map((t) => {
        const m = RESOURCE_META[t]
        const Icon = m.icon
        return (
          <li key={t} className="inline-flex h-6 items-center gap-1 rounded-xs border border-line-strong px-1.5 font-mono text-[0.66rem] text-text-2">
            <Icon className="size-3" aria-hidden /><span>{m.short}</span>
          </li>
        )
      })}
    </ul>
  )
}
