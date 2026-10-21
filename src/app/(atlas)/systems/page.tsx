import type { Metadata } from 'next'
import { PageHero } from '@/components/PageHero'
import { SystemsExplorer } from '@/components/systems/SystemsExplorer'
import { SYSTEMS } from '@/data/systems'

export const metadata: Metadata = {
  title: 'Systems explorer',
  description: 'Filter and compare 120+ public company design systems by industry, stack, token pipeline, Figma kit and source model.',
}

export default function SystemsPage() {
  const open = SYSTEMS.filter((s) => s.source === 'open').length
  const figma = SYSTEMS.filter((s) => s.figma === 'official').length
  return (
    <>
      <PageHero
        index="02"
        eyebrow="Company design systems"
        title={
          <>
            Every system, <span className="serif">one filter</span> away.
          </>
        }
        intro="Docs and repos for enterprise consoles, B2B SaaS, fintech, public sector and the libraries you can install today. Open any card for details, or pick two to four and compare them side by side."
        stats={[
          { value: String(SYSTEMS.length), label: 'Systems' },
          { value: String(open), label: 'Open source' },
          { value: String(figma), label: 'Official Figma kits' },
        ]}
      />
      <SystemsExplorer />
    </>
  )
}
