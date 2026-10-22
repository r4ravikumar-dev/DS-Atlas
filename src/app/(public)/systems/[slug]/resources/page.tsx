import type { Metadata } from 'next'
import { getPage, optional } from '@/lib/api/server'
import { loadSystem, systemOrRedirect } from '@/lib/api/systems'
import type { StorybookStory } from '@/lib/api/types'
import { ResourcePanel } from '@/components/details/ResourcePanel'
import { ExternalLink } from '@/components/kit/external-link'

type Params = { params: Promise<{ slug: string }> }

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const s = await loadSystem((await params).slug)
  return { title: `${s.name} resources`, description: `Official website, documentation, GitHub, Figma and Storybook links for ${s.name}.`, alternates: { canonical: `/systems/${s.slug}/resources` } }
}

/** Official resources and documentation entry points, plus the system's public Storybook. */
export default async function SystemResources({ params }: Params) {
  const s = await systemOrRedirect((await params).slug, '/resources')
  const stories = s.storybook_projects.length
    ? await optional(getPage<StorybookStory>('/storybook/stories', { query: { system_id: s.id, entry_type: 'story', page_size: 20 }, tags: [`system:${s.id}`] }))
    : null
  return (
    <div className="flex flex-col gap-16">
      <section aria-labelledby="res-title">
        <h2 id="res-title" className="mb-6 text-section font-medium">Official resources</h2>
        <ResourcePanel resources={s.resources} />
      </section>
      {s.storybook_projects.length > 0 && (
        <section aria-labelledby="sb-title">
          <h2 id="sb-title" className="mb-6 text-section font-medium">Storybook</h2>
          <ul className="grid gap-3 md:grid-cols-2">
            {s.storybook_projects.map((p) => (
              <li key={String(p.id)} className="flex flex-col gap-2 rounded-sm border border-line p-5">
                <p className="text-card font-medium">{String(p.title)}</p>
                <p className="font-mono text-meta text-muted">{Number(p.stories_extracted ?? 0).toLocaleString()} stories · {Number(p.variants_extracted ?? 0).toLocaleString()} variants</p>
                <ExternalLink href={String(p.resolved_url ?? p.storybook_url)} className="w-fit text-meta">Open Storybook</ExternalLink>
              </li>
            ))}
          </ul>
          {stories && stories.data.length > 0 && (
            <ul className="mt-6 divide-y divide-line border-y border-line">
              {stories.data.map((st) => (
                <li key={st.id} className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 py-3">
                  <span><span className="text-text">{st.name}</span> <span className="font-mono text-[0.72rem] text-muted">{st.title}</span></span>
                  <ExternalLink href={st.story_url} className="text-meta">Open story</ExternalLink>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
      {(s.logo || s.cover) && (
        <section aria-labelledby="att-title" className="border-t border-line pt-8">
          <h2 id="att-title" className="eyebrow mb-3">Image attribution</h2>
          <ul className="flex flex-col gap-1.5 text-[0.78rem] text-muted">
            {[s.logo, s.cover].filter(Boolean).map((a) => (
              <li key={a!.url}>{a!.alt ?? 'Image'} — {a!.attribution ?? `published on ${a!.source_host}`}. Referenced from the owner&apos;s site; not affiliated with or endorsed by its owner.</li>
            ))}
          </ul>
        </section>
      )}
    </div>
  )
}
