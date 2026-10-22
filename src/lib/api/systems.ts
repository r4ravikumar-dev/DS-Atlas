import 'server-only'
import { cache } from 'react'
import { notFound, permanentRedirect } from 'next/navigation'
import { BackendError, getItem } from './server'
import type { SystemDetail } from './types'

export interface PublicAsset { url: string; alt?: string | null; width?: number | null; height?: number | null; page_url?: string | null; source_host?: string | null; attribution?: string | null; license?: string | null }
/** The public presentation of a system (internal verification/crawl fields are omitted by the API). */
export type PublicSystem = SystemDetail & { slug: string; logo?: PublicAsset | null; cover?: PublicAsset | null }

/** One request per render for the layout, metadata and page (React cache). */
export const loadSystem = cache(async (ref: string): Promise<PublicSystem> => {
  if (!/^[a-z0-9-]{1,120}$/i.test(ref)) notFound()
  try {
    return await getItem<PublicSystem>(`/design-systems/${encodeURIComponent(ref)}`, { tags: ['systems', `system-ref:${ref}`] })
  } catch (e) {
    if (e instanceof BackendError && e.status === 404) notFound()
    throw e
  }
})

/** Numeric ids (old URLs, merged records) and outdated slugs land on the canonical slug URL. */
export async function systemOrRedirect(ref: string, rest = ''): Promise<PublicSystem> {
  const s = await loadSystem(ref)
  if (s.slug && s.slug !== ref) permanentRedirect(`/systems/${s.slug}${rest}`)
  return s
}

export const systemPath = (s: { slug?: string | null; id: number }) => `/systems/${s.slug ?? s.id}`
