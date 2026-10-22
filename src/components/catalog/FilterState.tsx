'use client'

import { createContext, useCallback, useContext, useTransition } from 'react'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { cn } from '@/lib/cn'

type Patch = Record<string, string | string[] | null | undefined>

interface Ctx {
  pending: boolean
  params: URLSearchParams
  /** Apply a patch to the URL; the server component re-renders with the new results. Resets to page 1 unless `page` is patched. */
  update: (patch: Patch) => void
}

const FilterCtx = createContext<Ctx | null>(null)

export function useFilters() {
  const c = useContext(FilterCtx)
  if (!c) throw new Error('useFilters must be used inside <FilterRoot>')
  return c
}

/** URL is the single source of truth for search, filters, sort and page — shareable and back-button friendly. */
export function FilterRoot({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const sp = useSearchParams()
  const [pending, start] = useTransition()
  const update = useCallback(
    (patch: Patch) => {
      const p = new URLSearchParams(sp.toString())
      for (const [k, v] of Object.entries(patch)) {
        p.delete(k)
        if (v === null || v === undefined || v === '' || (Array.isArray(v) && v.length === 0)) continue
        if (Array.isArray(v)) v.forEach((x) => p.append(k, x))
        else p.set(k, v)
      }
      if (!('page' in patch)) p.delete('page')
      const qs = p.toString()
      start(() => router.push(qs ? `${pathname}?${qs}` : pathname, { scroll: false }))
    },
    [sp, router, pathname],
  )
  return <FilterCtx.Provider value={{ pending, params: new URLSearchParams(sp.toString()), update }}>{children}</FilterCtx.Provider>
}

/** Wraps server-rendered results: dims and marks them busy while new results are on their way. */
export function Results({ children, className }: { children: React.ReactNode; className?: string }) {
  const { pending } = useFilters()
  return (
    <div aria-busy={pending} className={cn('transition-opacity duration-200', pending && 'pointer-events-none opacity-45', className)}>
      {children}
    </div>
  )
}
