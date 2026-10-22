'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { motion } from 'motion/react'
import { spring } from '@/lib/motion/tokens'
import { cn } from '@/lib/cn'

/** Workspace navigation for one design system. Every tab queries the backend scoped to this system. */
export function SystemTabs({ base, tabs }: { base: string; tabs: { href: string; label: string; count?: number }[] }) {
  const pathname = usePathname()
  const active = (href: string) => (href === '' ? pathname === base : pathname === base + href || pathname.startsWith(`${base}${href}/`))
  return (
    <nav aria-label="Design system sections" className="sticky top-(--header-h) z-30 border-b border-line bg-glass backdrop-blur-xl">
      <ul className="container-page flex gap-1 overflow-x-auto [scrollbar-width:none]">
        {tabs.map((t) => {
          const on = active(t.href)
          return (
            <li key={t.href} className="shrink-0">
              <Link href={base + t.href} aria-current={on ? 'page' : undefined}
                className={cn('focus-ring relative inline-flex h-12 items-center gap-2 px-3 text-[0.9rem] transition-colors', on ? 'text-text' : 'text-muted hover:text-text')}>
                {t.label}
                {t.count !== undefined && t.count > 0 && <span className="font-mono text-[0.68rem] text-faint tabular-nums">{t.count.toLocaleString()}</span>}
                {on && <motion.span layoutId="system-tab" transition={spring.snappy} className="absolute inset-x-2 bottom-0 h-0.5 bg-accent" aria-hidden />}
              </Link>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}
