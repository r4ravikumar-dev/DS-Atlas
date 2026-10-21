import type { Metadata } from 'next'
import { PageHero } from '@/components/PageHero'
import { Checklist } from '@/components/Checklist'
import { CHECKLIST, CHECKLIST_TOTAL } from '@/data/checklist'

export const metadata: Metadata = {
  title: 'Design system checklist',
  description: 'An interactive checklist for design language, foundations, components and maintenance. Progress is saved in your browser and exportable as Markdown.',
}

export default function ChecklistPage() {
  return (
    <>
      <PageHero
        index="06"
        eyebrow="Plan & govern"
        title={
          <>
            Build only what you <span className="serif">need now.</span>
          </>
        }
        intro="Work through design language, foundations, 30 core components and the maintenance practices that keep a system alive. Tick items as you go — progress stays in this browser, and you can export it as a Markdown checklist for your team."
        stats={[
          { value: String(CHECKLIST.length), label: 'Areas' },
          { value: String(CHECKLIST.reduce((n, c) => n + c.sections.length, 0)), label: 'Sections' },
          { value: String(CHECKLIST_TOTAL), label: 'Checks' },
        ]}
      />
      <Checklist />
    </>
  )
}
