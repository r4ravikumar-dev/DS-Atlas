import type { Metadata } from 'next'
import { getPage, optional } from '@/lib/api/server'
import { loadSystem, systemOrRedirect } from '@/lib/api/systems'
import type { Token } from '@/lib/api/types'
import { FoundationsViz } from '@/components/details/FoundationsViz'
import { EmptyState, RecoveryLink } from '@/components/kit/states'

type Params = { params: Promise<{ slug: string }> }
const CATEGORIES = ['color', 'typography', 'spacing', 'sizing', 'radius', 'shadow', 'motion', 'border']

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const s = await loadSystem((await params).slug)
  return { title: `${s.name} foundations`, description: `Colour, type, spacing, radius, elevation and motion values published by ${s.name}.`, alternates: { canonical: `/systems/${s.slug}/foundations` } }
}

/** Foundations drawn only from this system's stored token values, fetched per category from its scoped endpoint. */
export default async function Foundations({ params }: Params) {
  const s = await systemOrRedirect((await params).slug, '/foundations')
  const pages = await Promise.all(CATEGORIES.map((category) => optional(getPage<Token>(`/design-systems/${s.id}/tokens`, { query: { category, page_size: 100 }, tags: [`system:${s.id}`] }))))
  const tokens = pages.flatMap((p) => p?.data ?? [])
  const viz = tokens.length ? FoundationsViz({ tokens, base: `/systems/${s.slug}` }) : null
  return viz ?? (
    <EmptyState title={`No machine-readable foundations collected for ${s.name}`} action={<RecoveryLink href={`/systems/${s.slug}/resources`}>View official resources</RecoveryLink>}>
      Foundations appear here when the system publishes tokens with CSS values in a source the index reads. Its documentation may still describe them — see Resources.
    </EmptyState>
  )
}
