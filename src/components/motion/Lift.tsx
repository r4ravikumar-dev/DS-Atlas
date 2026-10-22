'use client'

import { motion, type HTMLMotionProps } from 'motion/react'
import { hover, spring } from '@/lib/motion/tokens'

/** Tactile hover/press response for cards. Transform-only, so it never causes layout work. */
export function Lift({ children, ...rest }: HTMLMotionProps<'div'>) {
  return (
    <motion.div whileHover={{ y: hover.lift }} whileTap={{ scale: 0.985 }} transition={spring.gentle} {...rest}>
      {children}
    </motion.div>
  )
}
