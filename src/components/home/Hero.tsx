'use client'

import { useRef } from 'react'
import Link from 'next/link'
import { motion, useMotionValue, useSpring, useTransform } from 'framer-motion'
import { ArrowRight, Search } from 'lucide-react'
import { gsap, SplitText, useGSAP } from '@/lib/gsap'
import { useApp } from '../Providers'
import styles from './Hero.module.scss'

const CHIPS = [
  { label: '--color-action-primary', x: '8%', y: '18%', depth: 30 },
  { label: '$type: "dimension"', x: '74%', y: '12%', depth: 50 },
  { label: 'space.400 = 16px', x: '82%', y: '58%', depth: 22 },
  { label: '<Button variant="ghost" />', x: '4%', y: '70%', depth: 40 },
  { label: 'aria-expanded', x: '58%', y: '82%', depth: 60 },
  { label: 'ease.standard', x: '30%', y: '6%', depth: 18 },
]

interface Props {
  stats: { value: number; label: string }[]
}

export function Hero({ stats }: Props) {
  const root = useRef<HTMLElement>(null)
  const { setPaletteOpen } = useApp()

  // Pointer parallax for floating token chips (Framer Motion springs)
  const mx = useMotionValue(0)
  const my = useMotionValue(0)
  const sx = useSpring(mx, { stiffness: 60, damping: 18 })
  const sy = useSpring(my, { stiffness: 60, damping: 18 })

  const onMove = (e: React.PointerEvent) => {
    const r = root.current!.getBoundingClientRect()
    mx.set((e.clientX - r.left) / r.width - 0.5)
    my.set((e.clientY - r.top) / r.height - 0.5)
  }

  useGSAP(
    () => {
      const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
      const title = root.current!.querySelector<HTMLElement>('[data-title]')!
      gsap.set(title, { autoAlpha: 1 })
      if (reduce) return

      const split = SplitText.create(title, { type: 'chars,words,lines', mask: 'lines' })
      const tl = gsap.timeline({ defaults: { ease: 'expo.out' }, delay: 0.35 })
      tl.from(split.chars, { yPercent: 120, duration: 1.2, stagger: 0.018 })
        .from('[data-hero-fade]', { y: 24, autoAlpha: 0, duration: 1, stagger: 0.08 }, '-=0.8')
        .from('[data-chip]', { scale: 0.6, autoAlpha: 0, duration: 0.9, stagger: 0.06, ease: 'back.out(2)' }, '-=0.9')

      // Count-up stats
      root.current!.querySelectorAll<HTMLElement>('[data-count]').forEach((el) => {
        const end = Number(el.dataset.count)
        const obj = { v: 0 }
        tl.to(obj, { v: end, duration: 1.6, ease: 'power3.out', onUpdate: () => (el.textContent = Math.round(obj.v).toString()) }, 0.9)
      })

      // Scroll-out: title drifts up & fades as you leave the hero
      gsap.to('[data-hero-inner]', {
        yPercent: -12,
        opacity: 0.2,
        ease: 'none',
        scrollTrigger: { trigger: root.current, start: 'top top', end: 'bottom top', scrub: true },
      })

      return () => split.revert()
    },
    { scope: root },
  )

  return (
    <section ref={root} className={styles.hero} onPointerMove={onMove}>
      <div className={styles.grid} aria-hidden />
      {CHIPS.map((c) => (
        <Chip key={c.label} {...c} sx={sx} sy={sy} />
      ))}

      <div className={`container ${styles.inner}`} data-hero-inner>
        <p className={styles.eyebrow} data-hero-fade>
          <span className={styles.live} /> The interactive design systems atlas · 2026
        </p>
        <h1 className={styles.title} data-title style={{ visibility: 'hidden' }}>
          Benchmark every <span className="serif">design system</span> worth studying.
        </h1>
        <p className={styles.lede} data-hero-fade>
          Separate <em>inspiration</em> — how the best teams document governance, tokens and usage — from the <em>codebases</em> you should actually
          ship on. Directories, repos, company systems, tools and a working checklist, in one place.
        </p>
        <div className={styles.ctas} data-hero-fade>
          <Link href="/systems" className={styles.primary}>
            Explore systems <ArrowRight size={18} />
          </Link>
          <button className={styles.secondary} onClick={() => setPaletteOpen(true)}>
            <Search size={16} /> Search everything <kbd>⌘K</kbd>
          </button>
        </div>
        <dl className={styles.stats} data-hero-fade>
          {stats.map((s) => (
            <div key={s.label}>
              <dd data-count={s.value}>{s.value}</dd>
              <dt>{s.label}</dt>
            </div>
          ))}
        </dl>
      </div>
    </section>
  )
}

function Chip({
  label,
  x,
  y,
  depth,
  sx,
  sy,
}: (typeof CHIPS)[number] & { sx: ReturnType<typeof useSpring>; sy: ReturnType<typeof useSpring> }) {
  const tx = useTransform(sx, (v) => v * depth * -1.6)
  const ty = useTransform(sy, (v) => v * depth * -1.6)
  return (
    <motion.span className={styles.chip} style={{ left: x, top: y, x: tx, y: ty }} data-chip aria-hidden>
      {label}
    </motion.span>
  )
}
