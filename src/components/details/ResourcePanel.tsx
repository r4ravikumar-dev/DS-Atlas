import type { ResourceOut } from '@/lib/api/types'
import { ExternalLink, prettyUrl } from '../kit/external-link'
import { PRIMARY_RESOURCES, RESOURCE_META } from '../catalog/resources'

const ORDER = [...PRIMARY_RESOURCES, 'additional_resource' as const]

/** Every official resource recorded for the system, grouped by type. Types with nothing recorded are simply omitted. */
export function ResourcePanel({ resources }: { resources: Pick<ResourceOut, 'id' | 'resource_type' | 'url' | 'label' | 'is_primary'>[] }) {
  const groups = ORDER.map((type) => ({ type, list: resources.filter((r) => r.resource_type === type).sort((a, b) => Number(b.is_primary) - Number(a.is_primary)) }))
    .filter((g) => g.list.length > 0)
  if (groups.length === 0) return <p className="text-meta text-muted">No official links have been recorded for this system yet.</p>
  return (
    <ul className="divide-y divide-line border-y border-line">
      {groups.map(({ type, list }) => {
        const m = RESOURCE_META[type]
        const Icon = m.icon
        return (
          <li key={type} className="grid gap-3 py-5 md:grid-cols-[13rem_1fr]">
            <p className="flex items-center gap-2 text-[0.92rem] text-text-2"><Icon className="size-4 text-muted" aria-hidden />{m.label}</p>
            <ul className="flex flex-col gap-2.5">
              {list.map((r) => (
                <li key={r.id}><ExternalLink href={r.url} className="w-fit font-mono text-[0.82rem] break-all text-text">{r.label ? `${r.label} — ${prettyUrl(r.url)}` : prettyUrl(r.url)}</ExternalLink></li>
              ))}
            </ul>
          </li>
        )
      })}
    </ul>
  )
}
