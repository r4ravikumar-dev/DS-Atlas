'use client'

import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import { usePathname } from 'next/navigation'
import Lenis from 'lenis'
import { MotionConfig } from 'framer-motion'
import { gsap, ScrollTrigger } from '@/lib/gsap'

type Theme = 'dark' | 'light'

interface AppCtx {
  theme: Theme
  toggleTheme: () => void
  paletteOpen: boolean
  setPaletteOpen: (open: boolean) => void
  lenis: React.RefObject<Lenis | null>
}

const Ctx = createContext<AppCtx | null>(null)

export function useApp() {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useApp must be used inside <Providers>')
  return ctx
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [theme, setTheme] = useState<Theme>('dark')
  const [paletteOpen, setPaletteOpen] = useState(false)
  const lenis = useRef<Lenis | null>(null)
  const pathname = usePathname()

  // Theme: the inline script in layout already set data-theme; mirror it into state.
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

  // Smooth scrolling with Lenis (editorial pages only — the data-dense platform keeps native scrolling).
  const isPlatform = pathname.startsWith('/platform')
  useEffect(() => {
    if (isPlatform || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    const instance = new Lenis({ duration: 1.1, smoothWheel: true })
    lenis.current = instance
    instance.on('scroll', ScrollTrigger.update)
    const tick = (time: number) => instance.raf(time * 1000)
    gsap.ticker.add(tick)
    gsap.ticker.lagSmoothing(0)
    return () => {
      gsap.ticker.remove(tick)
      instance.destroy()
      lenis.current = null
    }
  }, [isPlatform])

  // Pause page scroll while the command palette is open.
  useEffect(() => {
    if (paletteOpen) lenis.current?.stop()
    else lenis.current?.start()
  }, [paletteOpen])

  // On every route: jump to top (or hash), then batch-reveal any [data-reveal] elements.
  useEffect(() => {
    const hash = window.location.hash
    if (!hash) lenis.current?.scrollTo(0, { immediate: true })

    let triggers: ScrollTrigger[] = []
    const id = window.setTimeout(() => {
      const els = gsap.utils.toArray<HTMLElement>('[data-reveal]:not([data-revealed])')
      triggers = ScrollTrigger.batch(els, {
        start: 'top 92%',
        once: true,
        onEnter: (batch) => {
          gsap.to(batch, {
            opacity: 1,
            y: 0,
            duration: 0.9,
            ease: 'power3.out',
            stagger: 0.07,
            overwrite: true,
          })
          batch.forEach((el) => el.setAttribute('data-revealed', ''))
        },
      })
      ScrollTrigger.refresh()
      if (hash) {
        const target = document.getElementById(decodeURIComponent(hash.slice(1)))
        if (target) lenis.current?.scrollTo(target, { offset: -100 })
      }
    }, 120)

    return () => {
      window.clearTimeout(id)
      triggers.forEach((t) => t.kill())
    }
  }, [pathname])

  // Global keyboard shortcut: ⌘K / Ctrl+K / "/" opens search (Atlas only; the platform has its own API search).
  useEffect(() => {
    if (isPlatform) return
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement
      const typing = target.closest('input, textarea, [contenteditable="true"]')
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setPaletteOpen((o) => !o)
      } else if (e.key === '/' && !typing) {
        e.preventDefault()
        setPaletteOpen(true)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [isPlatform])

  return (
    <Ctx.Provider value={{ theme, toggleTheme, paletteOpen, setPaletteOpen, lenis }}>
      <MotionConfig reducedMotion="user" transition={{ type: 'spring', stiffness: 380, damping: 34 }}>
        {children}
      </MotionConfig>
    </Ctx.Provider>
  )
}
