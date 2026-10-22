'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Popover } from 'radix-ui'
import { motion } from 'motion/react'
import { ChevronDown, Menu, Moon, Search, Settings, Sun } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api/client'
import { qk } from '@/lib/api/keys'
import type { Item, User } from '@/lib/api/types'
import { spring } from '@/lib/motion/tokens'
import { cn } from '@/lib/cn'
import { useApp } from '../Providers'
import { Sheet } from '../kit/sheet'
import { CommandSearch } from './CommandSearch'
import { Wordmark } from './Wordmark'
import { PRIMARY_NAV, RESOURCES_NAV } from './nav'

/** Admin entry point only for a signed-in administrator; anonymous visitors never trigger the session check. */
function useAdminLink() {
  const [maybe, setMaybe] = useState(false)
  useEffect(() => setMaybe(/(?:^|;\s*)dsrp_csrf=/.test(document.cookie)), [])
  const me = useQuery({ queryKey: qk.me, queryFn: ({ signal }) => api<Item<User>>('/auth/me', { signal }).then((r) => r.data), enabled: maybe, retry: false, staleTime: 60_000 })
  return me.data?.role === 'admin'
}

export function SiteHeader() {
  const pathname = usePathname()
  const { theme, toggleTheme } = useApp()
  const [searchOpen, setSearchOpen] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)
  const admin = useAdminLink()

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const typing = e.target instanceof HTMLElement && (e.target.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName))
      if ((e.key === 'k' && (e.metaKey || e.ctrlKey)) || (e.key === '/' && !typing)) {
        e.preventDefault()
        setSearchOpen(true)
      }
    }
    const onScroll = () => setScrolled(window.scrollY > 8)
    onScroll()
    window.addEventListener('keydown', onKey)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => (window.removeEventListener('keydown', onKey), window.removeEventListener('scroll', onScroll))
  }, [])
  useEffect(() => setMenuOpen(false), [pathname])

  const isActive = (match: string[]) => match.some((m) => pathname === m || pathname.startsWith(`${m}/`))
  const resourcesActive = RESOURCES_NAV.some((r) => isActive([r.href]))

  return (
    <header className={cn('sticky top-0 z-40 border-b transition-[background-color,border-color] duration-300', scrolled ? 'border-line bg-glass backdrop-blur-xl' : 'border-transparent bg-transparent')}>
      <div className="container-page flex h-(--header-h) items-center gap-3 sm:gap-6">
        <Link href="/" className="focus-ring min-w-0 shrink" aria-label="Design Systems Directory — home"><Wordmark /></Link>

        <nav aria-label="Primary" className="hidden xl:block">
          <ul className="flex items-center gap-1">
            {PRIMARY_NAV.map((n) => (
              <li key={n.href}><NavLink href={n.href} active={isActive(n.match)}>{n.label}</NavLink></li>
            ))}
            <li>
              <Popover.Root>
                <Popover.Trigger className={cn('focus-ring group relative inline-flex h-9 items-center gap-1 rounded-sm px-3 text-[0.9rem] transition-colors', resourcesActive ? 'text-text' : 'text-muted hover:text-text')}>
                  Resources <ChevronDown className="size-3.5 transition-transform group-data-[state=open]:rotate-180" aria-hidden />
                  {resourcesActive && <ActiveBar />}
                </Popover.Trigger>
                <Popover.Portal>
                  <Popover.Content sideOffset={10} align="start" className="z-50 w-80 rounded-md border border-line-strong bg-bg p-2 shadow-2 data-[state=open]:animate-[pop_0.2s_var(--ease-out)]">
                    <ul>
                      {RESOURCES_NAV.map((r) => (
                        <li key={r.href}>
                          <Popover.Close asChild>
                            <Link href={r.href} className="focus-ring block rounded-sm px-3 py-2.5 hover:bg-surface-2">
                              <span className="block text-[0.92rem] text-text">{r.label}</span>
                              <span className="block text-meta text-muted">{r.hint}</span>
                            </Link>
                          </Popover.Close>
                        </li>
                      ))}
                    </ul>
                  </Popover.Content>
                </Popover.Portal>
              </Popover.Root>
            </li>
          </ul>
        </nav>

        <div className="ml-auto flex items-center gap-1.5">
          <button type="button" onClick={() => setSearchOpen(true)} aria-label="Search the directory"
            className="focus-ring flex h-9 items-center gap-2 rounded-sm border-line-strong bg-surface/60 text-meta text-muted transition-colors hover:border-text/30 hover:text-text max-sm:size-9 max-sm:justify-center sm:w-56 sm:border sm:pr-1.5 sm:pl-3">
            <Search className="size-4 sm:size-3.5" aria-hidden />
            <span className="hidden sm:inline">Search the directory</span>
            <kbd className="ml-auto hidden rounded-xs border border-line px-1.5 font-mono text-[0.65rem] sm:block">⌘K</kbd>
          </button>
          {admin && (
            <Link href="/admin" className="focus-ring hidden h-9 items-center gap-1.5 rounded-sm px-3 text-meta text-muted hover:text-text md:inline-flex"><Settings className="size-3.5" aria-hidden />Admin</Link>
          )}
          <button type="button" onClick={toggleTheme} className="focus-ring grid size-9 place-items-center rounded-sm text-muted hover:bg-surface-2 hover:text-text" aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}>
            {theme === 'dark' ? <Sun className="size-4" /> : <Moon className="size-4" />}
          </button>
          <button type="button" onClick={() => setMenuOpen(true)} className="focus-ring grid size-9 place-items-center rounded-sm text-muted hover:bg-surface-2 hover:text-text xl:hidden" aria-label="Open menu" aria-expanded={menuOpen}>
            <Menu className="size-4" />
          </button>
        </div>
      </div>

      <CommandSearch open={searchOpen} onOpenChange={setSearchOpen} />
      <Sheet open={menuOpen} onOpenChange={setMenuOpen} title="Menu">
        <nav aria-label="Mobile">
          <ul className="flex flex-col">
            {[{ href: '/', label: 'Home', match: ['/__home'] }, ...PRIMARY_NAV].map((n) => (
              <li key={n.href}>
                <Link href={n.href} aria-current={(n.href === '/' ? pathname === '/' : isActive(n.match)) ? 'page' : undefined}
                  className="focus-ring flex items-center justify-between border-b border-line py-4 text-xl tracking-tight aria-[current=page]:text-accent-text">{n.label}</Link>
              </li>
            ))}
          </ul>
          <p className="eyebrow mt-8 mb-2">Resources</p>
          <ul>
            {RESOURCES_NAV.map((r) => (
              <li key={r.href}><Link href={r.href} className="focus-ring block py-2.5 text-text-2 hover:text-text">{r.label}</Link></li>
            ))}
            {admin && <li><Link href="/admin" className="focus-ring block py-2.5 text-text-2 hover:text-text">Admin</Link></li>}
          </ul>
        </nav>
      </Sheet>
    </header>
  )
}

function NavLink({ href, active, children }: { href: string; active: boolean; children: React.ReactNode }) {
  return (
    <Link href={href} aria-current={active ? 'page' : undefined} className={cn('focus-ring relative inline-flex h-9 items-center rounded-sm px-3 text-[0.9rem] transition-colors', active ? 'text-text' : 'text-muted hover:text-text')}>
      {children}
      {active && <ActiveBar />}
    </Link>
  )
}

/** Shared-layout underline that glides between the active items. */
function ActiveBar() {
  return <motion.span layoutId="nav-active" className="absolute inset-x-3 -bottom-[13px] h-px bg-accent" transition={spring.snappy} aria-hidden />
}
