'use client'

import { createContext, useCallback, useContext, useEffect, useState } from 'react'

type Theme = 'dark' | 'light'

interface AppCtx {
  theme: Theme
  toggleTheme: () => void
}

const Ctx = createContext<AppCtx | null>(null)

export function useApp() {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useApp must be used inside <Providers>')
  return ctx
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [theme, setTheme] = useState<Theme>('dark')

  // The inline script in the root layout already set data-theme before paint; mirror it into state.
  useEffect(() => {
    const current = document.documentElement.dataset.theme as Theme | undefined
    if (current) setTheme(current)
  }, [])

  const toggleTheme = useCallback(() => {
    setTheme((t) => {
      const next = t === 'dark' ? 'light' : 'dark'
      document.documentElement.dataset.theme = next
      try {
        localStorage.setItem('dsa-theme', next)
      } catch {}
      return next
    })
  }, [])

  return <Ctx.Provider value={{ theme, toggleTheme }}>{children}</Ctx.Provider>
}
