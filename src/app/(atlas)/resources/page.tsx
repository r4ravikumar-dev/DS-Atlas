import type { Metadata } from 'next'
import { PageHero } from '@/components/PageHero'
import { ResourceLibrary } from '@/components/ResourceLibrary'
import { RESOURCE_GROUPS } from '@/data/resources'

export const metadata: Metadata = {
  title: 'Resource library',
  description: 'Design-system platforms, AI tools, Figma plugins, accessibility checkers, metrics, UI kits, books, podcasts, talks and open Figma files.',
}

export default function ResourcesPage() {
  const total = RESOURCE_GROUPS.reduce((n, g) => n + g.items.length, 0)
  return (
    <>
      <PageHero
        index="04"
        eyebrow="The Design System Guide × designsystems.com"
        title={
          <>
            Tools, talks & <span className="serif">tomes.</span>
          </>
        }
        intro="Everything around the system itself: documentation platforms, AI and Figma automation, colour and accessibility tooling, adoption metrics, starter kits, and the books, podcasts and articles practitioners keep coming back to."
        stats={[
          { value: String(total), label: 'Resources' },
          { value: String(RESOURCE_GROUPS.length), label: 'Categories' },
        ]}
      />
      <ResourceLibrary />
    </>
  )
}
