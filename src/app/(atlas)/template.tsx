'use client'

import { motion } from 'framer-motion'
import { ScrollTrigger } from '@/lib/gsap'

/** Re-mounts on every navigation, giving each page an enter transition plus a curtain wipe. */
export default function Template({ children }: { children: React.ReactNode }) {
  return (
    <>
      <motion.div
        aria-hidden
        initial={{ scaleY: 1 }}
        animate={{ scaleY: 0 }}
        transition={{ duration: 0.7, ease: [0.76, 0, 0.24, 1] }}
        style={{
          position: 'fixed',
          inset: 0,
          zIndex: 80,
          background: 'var(--accent)',
          transformOrigin: 'top',
          pointerEvents: 'none',
        }}
      />
      <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7, delay: 0.15, ease: [0.22, 1, 0.36, 1] }}
        onAnimationComplete={() => ScrollTrigger.refresh()}
      >
        {children}
      </motion.div>
    </>
  )
}
