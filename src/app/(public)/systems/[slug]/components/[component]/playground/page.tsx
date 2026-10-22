import type { Metadata } from 'next'
import Link from 'next/link'
import { notFound } from 'next/navigation'
import { ArrowLeft, BookOpen } from 'lucide-react'
import { BackendError, getItem } from '@/lib/api/server'
import { loadSystem } from '@/lib/api/systems'
import type { PlaygroundSchema } from '@/playground/schema'
import { Playground } from '@/components/playground/Playground'
import { EmptyState, RecoveryLink } from '@/components/kit/states'
import { Button } from '@/components/kit/button'

type Params = { params: Promise<{ slug: string; component: string }> }

async function load(slug: string, ref: string) {
  const s = await loadSystem(slug)
  if (!/^[a-z0-9-]{1,160}$/i.test(ref)) notFound()
  try {
    const c = await getItem<{ id: number; name: string; slug: string }>(`/design-systems/${s.id}/components/${encodeURIComponent(ref)}`, { tags: [`system:${s.id}`] })
    const schema = await getItem<PlaygroundSchema>(`/components/${c.id}/playground-schema`, { tags: [`component:${c.id}`] })
    return { s, c, schema }
  } catch (e) {
    if (e instanceof BackendError && e.status === 404) notFound()
    throw e
  }
}

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const { slug, component } = await params
  const { s, c } = await load(slug, component)
  return { title: `${c.name} playground — ${s.name}`, description: `Change ${s.name} ${c.name} properties and see the result live.`, alternates: { canonical: `/systems/${s.slug}/components/${c.slug}/playground` } }
}

export default async function ComponentPlayground({ params }: Params) {
  const { slug, component } = await params
  const { s, c, schema } = await load(slug, component)
  const back = `/systems/${s.slug}/components/${c.slug}`
  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <Link href={back} className="focus-ring mb-3 inline-flex items-center gap-1.5 text-meta text-muted hover:text-text"><ArrowLeft className="size-3.5" aria-hidden />{c.name} API</Link>
          <h2 className="text-section font-medium">{c.name} <span className="font-serif font-normal text-muted italic">playground</span></h2>
        </div>
        {schema.documentation_url && <Button asChild variant="secondary"><a href={schema.documentation_url} target="_blank" rel="noopener noreferrer nofollow"><BookOpen className="size-4" aria-hidden />Official documentation<span className="sr-only">(opens in a new tab)</span></a></Button>}
      </div>
      {schema.tier === 'docs' ? (
        <EmptyState title="No interactive preview for this component yet" action={<RecoveryLink href={back}>See its documented API</RecoveryLink>}>
          {schema.limitations.join(' ')}
        </EmptyState>
      ) : <Playground schema={schema} />}
    </div>
  )
}
