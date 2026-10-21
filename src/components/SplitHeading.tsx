'use client'

import { useRef } from 'react'
import { gsap, SplitText, useGSAP } from '@/lib/gsap'

interface Props {
  as?: 'h1' | 'h2'
  className?: string
  children: React.ReactNode
  delay?: number
  /** Animate on scroll into view instead of on mount */
  onScroll?: boolean
}

/** Heading whose words rise in line-by-line via GSAP SplitText with a mask. */
export function SplitHeading({ as: Tag = 'h1', className, children, delay = 0.1, onScroll = false }: Props) {
  const ref = useRef<HTMLHeadingElement>(null)

  useGSAP(
    () => {
      if (!ref.current) return
      if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        gsap.set(ref.current, { autoAlpha: 1 })
        return
      }
      const split = SplitText.create(ref.current, { type: 'lines,words', mask: 'lines', linesClass: 'split-line' })
      gsap.set(ref.current, { autoAlpha: 1 })
      gsap.from(split.words, {
        yPercent: 110,
        rotate: 4,
        duration: 1.05,
        ease: 'expo.out',
        stagger: 0.045,
        delay,
        scrollTrigger: onScroll ? { trigger: ref.current, start: 'top 85%', once: true } : undefined,
      })
      return () => split.revert()
    },
    { scope: ref },
  )

  return (
    <Tag ref={ref} className={className} style={{ visibility: 'hidden' }}>
      {children}
    </Tag>
  )
}
