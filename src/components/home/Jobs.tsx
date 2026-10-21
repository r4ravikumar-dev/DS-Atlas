'use client'

import { useRef } from 'react'
import Link from 'next/link'
import { ArrowUpRight } from 'lucide-react'
import { gsap, ScrollTrigger, useGSAP } from '@/lib/gsap'
import styles from './Jobs.module.scss'

const JOBS = [
  {
    n: '01',
    title: 'Audit component patterns',
    body: 'Before you build an Accordion or Combobox, see how 30 companies name, code and document it. Use galleries and live Storybooks to benchmark states and props.',
    tools: ['The Component Gallery', 'Storybook Showcase', 'Adele'],
    href: '/directories',
    cta: 'Directories & repos',
    color: 'var(--sky)',
  },
  {
    n: '02',
    title: 'Structure design tokens',
    body: 'Adopt the W3C $value / $type format from day one, study Primer & Spectrum taxonomies, and compile once to CSS, Swift and Compose with Style Dictionary.',
    tools: ['W3C DTCG', 'Style Dictionary', 'Primer Primitives'],
    href: '/systems',
    cta: 'Compare token pipelines',
    color: 'var(--violet)',
  },
  {
    n: '03',
    title: 'Choose a code foundation',
    body: 'Don’t fork Carbon or Polaris — they’re hard-coded to someone else’s workflows. Own your code with headless primitives or ship fast on a themeable library.',
    tools: ['shadcn/ui', 'Radix / Base UI', 'React Aria'],
    href: '/foundations',
    cta: 'Find your foundation',
    color: 'var(--coral)',
  },
  {
    n: '04',
    title: 'Plan, govern & measure',
    body: 'Only build what your product needs right now. Track foundations, components and maintenance with the checklist, then prove value with adoption metrics.',
    tools: ['Design System Checklist', 'Omlet', 'React Scanner'],
    href: '/checklist',
    cta: 'Open the checklist',
    color: 'var(--mint)',
  },
]

/** Pinned section that scrolls its panels horizontally as you scroll down (desktop only). */
export function Jobs() {
  const root = useRef<HTMLElement>(null)
  const track = useRef<HTMLDivElement>(null)

  useGSAP(
    () => {
      const mm = gsap.matchMedia()
      mm.add('(min-width: 900px) and (prefers-reduced-motion: no-preference)', () => {
        const el = track.current!
        const distance = () => el.scrollWidth - window.innerWidth
        const tween = gsap.to(el, {
          x: () => -distance(),
          ease: 'none',
          scrollTrigger: {
            trigger: root.current,
            start: 'top top',
            end: () => `+=${distance()}`,
            pin: true,
            scrub: 0.8,
            invalidateOnRefresh: true,
          },
        })
        // Progress bar + per-panel parallax on the big numbers
        gsap.to('[data-progress]', {
          scaleX: 1,
          ease: 'none',
          scrollTrigger: { trigger: root.current, start: 'top top', end: () => `+=${distance()}`, scrub: true },
        })
        gsap.utils.toArray<HTMLElement>('[data-num]').forEach((num) => {
          gsap.fromTo(
            num,
            { xPercent: 30 },
            {
              xPercent: -30,
              ease: 'none',
              scrollTrigger: { trigger: num.parentElement, containerAnimation: tween, start: 'left right', end: 'right left', scrub: true },
            },
          )
        })
        return () => ScrollTrigger.getAll().forEach((t) => t.vars.containerAnimation === tween && t.kill())
      })
      return () => mm.revert()
    },
    { scope: root },
  )

  return (
    <section ref={root} className={styles.section} aria-labelledby="jobs-title">
      <div className={styles.head}>
        <div className="container">
          <p className="mono">Four jobs, four toolkits</p>
          <h2 id="jobs-title">
            What problem are you <span className="serif">solving?</span>
          </h2>
        </div>
        <div className={styles.bar}>
          <span data-progress />
        </div>
      </div>
      <div ref={track} className={styles.track}>
        {JOBS.map((j) => (
          <article key={j.n} className={styles.panel} style={{ '--c': j.color } as React.CSSProperties}>
            <span className={styles.num} data-num aria-hidden>
              {j.n}
            </span>
            <div className={styles.body}>
              <h3>{j.title}</h3>
              <p>{j.body}</p>
              <ul>
                {j.tools.map((t) => (
                  <li key={t}>{t}</li>
                ))}
              </ul>
              <Link href={j.href} className={styles.cta}>
                {j.cta} <ArrowUpRight size={16} />
              </Link>
            </div>
          </article>
        ))}
      </div>
    </section>
  )
}
