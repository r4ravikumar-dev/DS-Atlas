'use client'

import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { MotionConfig } from 'motion/react'

type Theme = 'dark' | 'light'

interface AppCtx {
  theme: Theme
  toggleTheme: () => void
  /** The visitor switched motion off on this site (independent of the OS setting, which is always honoured too). */
  motionOff: boolean
  toggleMotion: () => void
}

const Ctx = createContext<AppCtx | null>(null)

export function useApp() {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useApp must be used inside <Providers>')
  return ctx
}

function save(key: string, value: string | null) {
  try {
    if (value === null) localStorage.removeItem(key)
    else localStorage.setItem(key, value)
  } catch {}
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [theme, setTheme] = useState<Theme>('dark')
  const [motionOff, setMotionOff] = useState(false)

  // The inline script in the root layout already set data-theme / data-motion before paint; mirror them into state.
  useEffect(() => {
    const d = document.documentElement.dataset
    if (d.theme) setTheme(d.theme as Theme)
    setMotionOff(d.motion === 'reduce')
  }, [])

  const toggleTheme = useCallback(() => {
    setTheme((t) => {
      const next = t === 'dark' ? 'light' : 'dark'
      document.documentElement.dataset.theme = next
      save('dsa-theme', next)
      return next
    })
  }, [])

  const toggleMotion = useCallback(() => {
    setMotionOff((off) => {
      const next = !off
      if (next) document.documentElement.dataset.motion = 'reduce'
      else delete document.documentElement.dataset.motion
      save('dsa-motion', next ? 'reduce' : null)
      return next
    })
  }, [])

  return (
    <Ctx.Provider value={{ theme, toggleTheme, motionOff, toggleMotion }}>
      <MotionConfig reducedMotion={motionOff ? 'always' : 'user'}>{children}</MotionConfig>
    </Ctx.Provider>
  )
}
