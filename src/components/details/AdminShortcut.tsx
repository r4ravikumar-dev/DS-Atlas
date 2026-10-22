'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useQuery } from '@tanstack/react-query'
import { Settings } from 'lucide-react'
import { api } from '@/lib/api/client'
import { qk } from '@/lib/api/keys'
import type { Item, User } from '@/lib/api/types'

/** For a signed-in administrator only: a link to the management view of this record. Anonymous visitors never call /auth/me. */
export function AdminShortcut({ href, label = 'Manage in admin' }: { href: string; label?: string }) {
  const [maybe, setMaybe] = useState(false)
  useEffect(() => setMaybe(/(?:^|;\s*)dsrp_csrf=/.test(document.cookie)), [])
  const me = useQuery({ queryKey: qk.me, queryFn: ({ signal }) => api<Item<User>>('/auth/me', { signal }).then((r) => r.data), enabled: maybe, retry: false, staleTime: 60_000 })
  if (me.data?.role !== 'admin') return null
  return <Link href={href} className="focus-ring inline-flex items-center gap-1.5 text-meta text-muted underline-offset-4 hover:text-text hover:underline"><Settings className="size-3.5" aria-hidden />{label}</Link>
}
