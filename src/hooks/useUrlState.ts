'use client'

import { useCallback, useMemo } from 'react'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'

/** Filters/pagination mirrored in the URL (shareable, back-button friendly). Arrays use repeated params. */
export function useUrlState() {
  const sp = useSearchParams()
  const router = useRouter()
  const pathname = usePathname()

  const get = useCallback((k: string, d = '') => sp.get(k) ?? d, [sp])
  const getAll = useCallback((k: string) => sp.getAll(k), [sp])
  const getNum = useCallback((k: string, d: number) => {
    const n = Number(sp.get(k))
    return Number.isFinite(n) && n > 0 ? n : d
  }, [sp])

  const set = useCallback(
    (patch: Record<string, string | number | boolean | string[] | null | undefined>, { resetPage = true } = {}) => {
      const p = new URLSearchParams(sp.toString())
      for (const [k, v] of Object.entries(patch)) {
        p.delete(k)
        if (v === null || v === undefined || v === '' || v === false || (Array.isArray(v) && v.length === 0)) continue
        if (Array.isArray(v)) v.forEach((x) => p.append(k, x))
        else p.set(k, String(v))
      }
      if (resetPage && !('page' in patch)) p.delete('page')
      const qs = p.toString()
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false })
    },
    [sp, router, pathname],
  )
  return useMemo(() => ({ get, getAll, getNum, set, params: sp }), [get, getAll, getNum, set, sp])
}
