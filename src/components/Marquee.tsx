'use client'

import { useRef } from 'react'
import { gsap, ScrollTrigger, useGSAP } from '@/lib/gsap'
import styles from './Marquee.module.scss'

interface Props {
  items: string[]
  reverse?: boolean
  speed?: number
}

/** Infinite GSAP marquee that speeds up with scroll velocity. */
export function Marquee({ items, reverse = false, speed = 40 }: Props) {
  const root = useRef<HTMLDivElement>(null)
  const track = useRef<HTMLDivElement>(null)

  useGSAP(
    () => {
      const el = track.current
      if (!el || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
      const half = el.scrollWidth / 2
      const tween = gsap.fromTo(
        el,
        { x: reverse ? -half : 0 },
        { x: reverse ? 0 : -half, duration: half / speed, ease: 'none', repeat: -1 },
      )
      const st = ScrollTrigger.create({
        trigger: root.current,
        start: 'top bottom',
        end: 'bottom top',
        onUpdate: (self) => {
          const boost = Math.min(Math.abs(self.getVelocity()) / 300, 5)
          gsap.to(tween, {
            timeScale: 1 + boost,
            duration: 0.25,
            overwrite: true,
            onComplete: () => void gsap.to(tween, { timeScale: 1, duration: 1.2, ease: 'power2.out' }),
          })
        },
      })
      return () => st.kill()
    },
    { scope: root },
  )

  const row = [...items, ...items]
  return (
    <div ref={root} className={styles.marquee} aria-hidden>
      <div ref={track} className={styles.track}>
        {row.map((item, i) => (
          <span key={i} className={styles.item}>
            {item}
            <i className={styles.dot} />
          </span>
        ))}
      </div>
    </div>
  )
}
