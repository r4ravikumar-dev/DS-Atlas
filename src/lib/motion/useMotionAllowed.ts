'use client'

import { useEffect, useState } from 'react'
import { useReducedMotion } from 'motion/react'
import { useApp } from '@/components/Providers'

export type MotionPreference = 'pending' | 'allowed' | 'reduced'

/**
 * 'allowed' when decorative motion may run: the OS doesn't ask for reduced motion and the visitor hasn't switched it off
 * here. 'pending' until mounted, so server HTML and the first client render agree. GSAP timelines and the WebGL scene
 * check this; Motion for React components get the same rule from <MotionConfig>.
 */
export function useMotionPreference(): MotionPreference {
  const osReduce = useReducedMotion()
  const { motionOff } = useApp()
  const [mounted, setMounted] = useState(false)
  useEffect(() => setMounted(true), [])
  if (!mounted) return 'pending'
  return osReduce || motionOff ? 'reduced' : 'allowed'
}

export const useMotionAllowed = () => useMotionPreference() === 'allowed'
