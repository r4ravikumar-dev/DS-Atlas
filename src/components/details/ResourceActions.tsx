import type { ResourceOut } from '@/lib/api/types'
import { cn } from '@/lib/cn'
import { buttonVariants } from '../kit/button'
import { PRIMARY_RESOURCES, RESOURCE_META } from '../catalog/resources'

/** Primary calls to action, rendered only for resources that exist (the API already omits links that no longer work). */
export function ResourceActions({ resources }: { resources: Pick<ResourceOut, 'id' | 'resource_type' | 'url' | 'is_primary'>[] }) {
  const pick = PRIMARY_RESOURCES.map((t) => resources.filter((r) => r.resource_type === t).sort((a, b) => Number(b.is_primary) - Number(a.is_primary))[0]).filter(Boolean)
  if (pick.length === 0) return null
  return (
    <ul className="flex flex-wrap gap-2">
      {pick.map((r, i) => {
        const m = RESOURCE_META[r.resource_type]
        const Icon = m.icon
        return (
          <li key={r.id}>
            <a href={r.url} target="_blank" rel="noopener noreferrer nofollow" className={cn(buttonVariants({ variant: i === 0 ? 'primary' : 'secondary', size: 'md' }))}>
              <Icon className="size-4" aria-hidden />{m.action}<span className="sr-only">(opens in a new tab)</span>
            </a>
          </li>
        )
      })}
    </ul>
  )
}
