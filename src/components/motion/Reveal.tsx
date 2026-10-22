'use client'

import { motion, type HTMLMotionProps } from 'motion/react'
import { distance, duration, ease, stagger, viewport, viewportList } from '@/lib/motion/tokens'

type Tag = 'div' | 'section' | 'li' | 'ul' | 'article' | 'header'

/**
 * Fade-up on first scroll into view. With reduced motion, <MotionConfig> turns the transform off and only opacity
 * remains (and content is never hidden from assistive tech: it's in the DOM from the start).
 */
export function Reveal({ as = 'div', delay = 0, y = distance.md, children, ...rest }: { as?: Tag; delay?: number; y?: number } & HTMLMotionProps<'div'>) {
  const M = motion[as] as typeof motion.div
  return (
    <M initial={{ opacity: 0, y }} whileInView={{ opacity: 1, y: 0 }} viewport={viewport} transition={{ duration: duration.slow, ease: ease.out, delay }} {...rest}>
      {children}
    </M>
  )
}

/** Parent that staggers its <StaggerItem> children once, when it scrolls into view. */
export function Stagger({ as = 'div', gap = stagger.base, children, ...rest }: { as?: Tag; gap?: number } & HTMLMotionProps<'div'>) {
  const M = motion[as] as typeof motion.div
  return (
    <M initial="hidden" whileInView="shown" viewport={viewportList} variants={{ hidden: {}, shown: { transition: { staggerChildren: gap } } }} {...rest}>
      {children}
    </M>
  )
}

export function StaggerItem({ as = 'div', children, ...rest }: { as?: Tag } & HTMLMotionProps<'div'>) {
  const M = motion[as] as typeof motion.div
  return (
    <M variants={{ hidden: { opacity: 0, y: distance.sm }, shown: { opacity: 1, y: 0, transition: { duration: duration.base, ease: ease.out } } }} {...rest}>
      {children}
    </M>
  )
}
