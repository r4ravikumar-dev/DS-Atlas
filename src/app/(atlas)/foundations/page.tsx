import type { Metadata } from 'next'
import { PageHero } from '@/components/PageHero'
import { FoundationPicker } from '@/components/FoundationPicker'
import { Section } from '@/components/Section'
import styles from './page.module.scss'

export const metadata: Metadata = {
  title: 'Code foundations',
  description: 'Choose a codebase foundation for your design system: shadcn/ui, Radix, Base UI, React Aria, Mantine or Ant Design.',
}

const LAYERS = [
  { n: 'L1', title: 'Tokens', body: 'W3C-format JSON → Style Dictionary → CSS variables, Swift, Compose.', eg: 'color.action.primary' },
  { n: 'L2', title: 'Primitives', body: 'Headless behaviour: focus, keyboard, ARIA. Radix, Base UI, React Aria.', eg: '<Dialog.Root>' },
  { n: 'L3', title: 'Components', body: 'Your styled, branded API — owned in your repo (shadcn-style).', eg: '<Button variant="primary">' },
  { n: 'L4', title: 'Patterns', body: 'Compositions with usage rules borrowed from Polaris, Carbon, GOV.UK.', eg: 'Empty state, Filter bar' },
]

export default function FoundationsPage() {
  return (
    <>
      <PageHero
        index="05"
        eyebrow="Production code foundations"
        title={
          <>
            Own the code. <span className="serif">Don’t fight the package.</span>
          </>
        }
        intro="Forking a company’s system creates friction — its components are wired to someone else’s business. Start from headless or copy-paste foundations instead. Move the sliders to rank them for your context."
      />
      <FoundationPicker />
      <Section
        kicker="Architecture"
        title={
          <>
            A system is <span className="serif">four layers</span> deep.
          </>
        }
        intro="Pick tools per layer rather than one monolith. Swap any layer without rewriting the others."
      >
        <ol className={styles.layers}>
          {LAYERS.map((l) => (
            <li key={l.n} data-reveal>
              <span className="mono">{l.n}</span>
              <h3>{l.title}</h3>
              <p>{l.body}</p>
              <code>{l.eg}</code>
            </li>
          ))}
        </ol>
      </Section>
    </>
  )
}
