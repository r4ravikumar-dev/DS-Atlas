import type { MetadataRoute } from 'next'
import { getPage } from '@/lib/api/server'
import { siteUrl } from '@/lib/site'

export const revalidate = 86400

type Row = { id: number; slug?: string | null; system_slug?: string | null; updated_at?: string | null; content_updated_at?: string | null }

/** Every page of a public listing (100 per request, the API maximum). */
async function all(path: string): Promise<Row[]> {
  try {
    const first = await getPage<Row>(path, { query: { page_size: 100 }, revalidate: 86400 })
    const rest = await Promise.all(Array.from({ length: Math.min(first.meta.total_pages, 60) - 1 }, (_, i) => getPage<Row>(path, { query: { page_size: 100, page: i + 2 }, revalidate: 86400 })))
    return [first, ...rest].flatMap((p) => p.data)
  } catch {
    return []
  }
}

/** Public pages only — generated from the canonical backend records. */
export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const base = siteUrl()
  const [systems, components] = await Promise.all([all('/design-systems'), all('/components')])
  const statics = ['', '/systems', '/components', '/tokens', '/patterns', '/playground', '/compare', '/storybook', '/about', '/attribution', '/privacy'].map((p) => ({ url: `${base}${p}`, changeFrequency: 'daily' as const, priority: p === '' ? 1 : 0.8 }))
  return [
    ...statics,
    ...systems.filter((s) => s.slug).flatMap((s) => ['', '/components', '/tokens', '/patterns'].map((sub) => ({ url: `${base}/systems/${s.slug}${sub}`, lastModified: s.content_updated_at ?? s.updated_at ?? undefined, changeFrequency: 'weekly' as const, priority: sub ? 0.6 : 0.7 }))),
    ...components.filter((c) => c.slug && c.system_slug).map((c) => ({ url: `${base}/systems/${c.system_slug}/components/${c.slug}`, changeFrequency: 'monthly' as const, priority: 0.5 })),
  ]
}
