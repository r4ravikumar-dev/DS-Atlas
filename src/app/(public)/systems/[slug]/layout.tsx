import Link from 'next/link'
import { Columns3 } from 'lucide-react'
import { getPage, optional } from '@/lib/api/server'
import { loadSystem } from '@/lib/api/systems'
import { SystemLogo } from '@/components/system/SystemLogo'
import { SystemTabs } from '@/components/system/SystemTabs'
import { ResourceActions } from '@/components/details/ResourceActions'
import { AdminShortcut } from '@/components/details/AdminShortcut'
import { Badge } from '@/components/kit/badge'

/**
 * Workspace for one design system: identity header (its own published icon when available) and the section tabs.
 * Every section below queries the backend with this system's id — nothing is fetched globally and filtered here.
 */
export default async function SystemLayout({ children, params }: { children: React.ReactNode; params: Promise<{ slug: string }> }) {
  const { slug } = await params
  const s = await loadSystem(slug)
  const base = `/systems/${s.slug}`
  const [patterns, playgrounds] = await Promise.all([
    optional(getPage(`/design-systems/${s.id}/patterns`, { query: { page_size: 1 }, tags: [`system:${s.id}`] })),
    optional(getPage(`/design-systems/${s.id}/playgrounds`, { query: { page_size: 1 }, tags: [`system:${s.id}`] })),
  ])
  const tabs = [
    { href: '', label: 'Overview' },
    { href: '/foundations', label: 'Foundations' },
    { href: '/components', label: 'Components', count: s.component_count },
    { href: '/tokens', label: 'Tokens', count: s.token_count },
    { href: '/patterns', label: 'Patterns', count: patterns?.meta.total_items },
    { href: '/playground', label: 'Playground', count: playgrounds?.meta.total_items },
    { href: '/resources', label: 'Resources' },
  ]
  return (
    <div>
      <header className="relative overflow-hidden border-b border-line">
        <div aria-hidden className="hairline-grid pointer-events-none absolute inset-0 opacity-40 [mask-image:linear-gradient(to_bottom,black,transparent)]" />
        <div className="container-page relative flex flex-col gap-6 pt-8 pb-8 md:pt-10">
          <nav aria-label="Breadcrumb" className="font-mono text-meta text-muted">
            <ol className="flex items-center gap-2"><li><Link href="/systems" className="focus-ring hover:text-text">Design systems</Link></li><li aria-hidden>/</li><li aria-current="page" className="truncate text-text-2">{s.name}</li></ol>
          </nav>
          <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <div className="flex items-center gap-5">
              <SystemLogo name={s.name} logo={s.logo} size="lg" />
              <div className="min-w-0">
                <h1 className="text-title font-medium">{s.name}</h1>
                {s.organization && <p className="mt-1 text-lg text-text-2">{s.organization}</p>}
                {s.frameworks.length + s.platforms.length > 0 && (
                  <ul className="mt-3 flex flex-wrap gap-1.5" aria-label="Technologies and platforms">
                    {[...new Set([...s.frameworks, ...s.platforms])].map((t) => <li key={t}><Badge>{t}</Badge></li>)}
                  </ul>
                )}
              </div>
            </div>
            <div className="flex flex-col items-start gap-3 lg:items-end">
              <ResourceActions resources={s.resources} />
              <div className="flex flex-wrap items-center gap-x-5 gap-y-2">
                <Link href={`/compare?kind=systems&ids=${s.id}&labels=${encodeURIComponent(s.name.replace(/\|/g, ' '))}`} className="focus-ring inline-flex items-center gap-1.5 text-meta text-text-2 underline-offset-4 hover:text-text hover:underline"><Columns3 className="size-3.5" aria-hidden />Compare with another system</Link>
                <AdminShortcut href={`/admin/systems/${s.id}`} />
              </div>
            </div>
          </div>
        </div>
      </header>
      <SystemTabs base={base} tabs={tabs} />
      <div className="container-page pt-10">{children}</div>
    </div>
  )
}
