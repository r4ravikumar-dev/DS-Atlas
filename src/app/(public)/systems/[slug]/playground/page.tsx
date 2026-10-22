import type { Metadata } from 'next'
import Link from 'next/link'
import { getPage } from '@/lib/api/server'
import { loadSystem, systemOrRedirect } from '@/lib/api/systems'
import type { Component } from '@/lib/api/types'
import { ComponentCard } from '@/components/catalog/ComponentCard'
import { EmptyState, RecoveryLink } from '@/components/kit/states'

type Params = { params: Promise<{ slug: string }> }

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const s = await loadSystem((await params).slug)
  return { title: `${s.name} playground`, description: `Interactive previews of ${s.name} components — change their properties and see the result.`, alternates: { canonical: `/systems/${s.slug}/playground` } }
}

export default async function SystemPlaygrounds({ params }: Params) {
  const s = await systemOrRedirect((await params).slug, '/playground')
  const list = await getPage<Component>(`/design-systems/${s.id}/playgrounds`, { query: { page_size: 100 }, tags: [`system:${s.id}`] })
  if (list.data.length === 0) {
    return (
      <EmptyState title={`No interactive previews for ${s.name} yet`} action={<RecoveryLink href={`/systems/${s.slug}/components`}>Browse {s.name} components</RecoveryLink>}>
        Previews are only offered where the system&apos;s own package can be rendered or a faithful adapter exists. Its components&apos; documented APIs are in <Link href={`/systems/${s.slug}/components`} className="focus-ring text-accent-text underline decoration-accent/40 underline-offset-4">Components</Link>.
      </EmptyState>
    )
  }
  const tier = list.data[0].playground
  return (
    <div className="flex flex-col gap-8">
      <p className="measure text-text-2">
        {tier === 'live' ? `Each preview renders ${s.name}'s own package at the documented version, isolated from the rest of the site.` : `Platform-rendered previews built from ${s.name}'s published component recipes and its stored theme tokens.`} Pick a component to change its properties.
      </p>
      <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {list.data.map((c) => (
          <li key={c.id}><ComponentCard c={{ ...c, slug: c.slug }} showSystem={false} /><Link href={`/systems/${s.slug}/components/${c.slug}/playground`} className="focus-ring mt-1 inline-block text-meta text-accent-text underline decoration-accent/40 underline-offset-4">Open playground</Link></li>
        ))}
      </ul>
    </div>
  )
}
