import Link from 'next/link'
import { ArrowUpRight, Check, X } from 'lucide-react'
import { Hero } from '@/components/home/Hero'
import { Jobs } from '@/components/home/Jobs'
import { Featured } from '@/components/home/Featured'
import { Marquee } from '@/components/Marquee'
import { SplitHeading } from '@/components/SplitHeading'
import { SYSTEMS } from '@/data/systems'
import { DIRECTORIES, REPOS, RESOURCE_GROUPS, FOUNDATIONS } from '@/data/resources'
import { CHECKLIST_TOTAL } from '@/data/checklist'
import styles from './page.module.scss'

const resourceCount = RESOURCE_GROUPS.reduce((n, g) => n + g.items.length, 0)

const EXPLORE = [
  { href: '/systems', n: SYSTEMS.length, label: 'Company systems', desc: 'Filter by industry, stack, token pipeline, Figma kit and source model.' },
  { href: '/directories', n: DIRECTORIES.length + REPOS.length, label: 'Directories & repos', desc: 'Meta-collections, awesome lists, token specs and pipelines.' },
  { href: '/resources', n: resourceCount, label: 'Library entries', desc: 'Platforms, plugins, a11y, books, podcasts, talks and open Figma files.' },
  { href: '/foundations', n: FOUNDATIONS.length, label: 'Code foundations', desc: 'Weight your priorities and get a ranked recommendation.' },
  { href: '/checklist', n: CHECKLIST_TOTAL, label: 'Checklist items', desc: 'Track language, foundations, components and maintenance — saved locally.' },
]

export default function Home() {
  const names = SYSTEMS.filter((s) => s.featured).map((s) => `${s.company} ${s.name}`)
  const others = SYSTEMS.filter((s) => !s.featured).slice(0, 28).map((s) => s.name)

  return (
    <>
      <Hero
        stats={[
          { value: SYSTEMS.length, label: 'Design systems' },
          { value: resourceCount + DIRECTORIES.length + REPOS.length, label: 'Tools & resources' },
          { value: CHECKLIST_TOTAL, label: 'Checklist items' },
          { value: 4, label: 'Source collections' },
        ]}
      />

      <Marquee items={names} />
      <Marquee items={others} reverse speed={30} />

      <Jobs />

      <Featured />

      <section className={`container ${styles.strategy}`} aria-labelledby="strategy-title">
        <p className="mono" data-reveal>
          Practical strategy
        </p>
        <SplitHeading as="h2" className={styles.h2} onScroll>
          Copy the <span className="serif">documentation</span>. Build on the <span className="serif">primitives</span>.
        </SplitHeading>
        <div className={styles.compare}>
          <div className={styles.col} data-reveal>
            <h3>
              <X size={18} /> Don’t
            </h3>
            <ul>
              <li>Fork Carbon or Polaris into your app — their components are hard-coded to their workflows and brand constraints.</li>
              <li>Fight upstream npm breaking changes for components you only half use.</li>
              <li>Invent a token format that only works in one tool.</li>
              <li>Build every component on day one.</li>
            </ul>
          </div>
          <div className={`${styles.col} ${styles.do}`} data-reveal>
            <h3>
              <Check size={18} /> Do
            </h3>
            <ul>
              <li>Own the code with shadcn/ui, or compose Radix, Base UI or React Aria primitives.</li>
              <li>Ship internal tools fast on Ant Design or Mantine when there’s no dedicated DS team.</li>
              <li>Use W3C <code>$value</code> / <code>$type</code> tokens so Figma Variables and code stay in sync.</li>
              <li>Borrow usage rules from Polaris, governance from Carbon and form patterns from GOV.UK.</li>
            </ul>
          </div>
        </div>
      </section>

      <section className={`container ${styles.explore}`} aria-label="Explore the atlas">
        {EXPLORE.map((e, i) => (
          <Link key={e.href} href={e.href} className={styles.row} data-reveal>
            <span className={styles.idx}>0{i + 1}</span>
            <span className={styles.n}>{e.n}</span>
            <span className={styles.label}>{e.label}</span>
            <span className={styles.desc}>{e.desc}</span>
            <ArrowUpRight className={styles.arrow} />
          </Link>
        ))}
      </section>
    </>
  )
}
