'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { BarChart3, BookOpen, Boxes, ClipboardCheck, Columns3, Database, FileText, Gauge, Layers, LogOut, Menu, Moon, Palette, PlusCircle, Search, Settings, ShieldCheck, Sun, Workflow, X } from 'lucide-react'
import { ApiError } from '@/lib/api/client'
import { isAdmin, useLogout, useMe } from '@/features/auth/api'
import { useApp } from '../Providers'
import { Skeleton } from '../ui'
import s from './Shell.module.scss'

const NAV = [
  { group: 'Overview', items: [{ href: '/platform', label: 'Dashboard', icon: Gauge, exact: true }] },
  {
    group: 'Collection',
    items: [
      { href: '/platform/add', label: 'Add source', icon: PlusCircle },
      { href: '/platform/sources', label: 'Sources', icon: Database },
      { href: '/platform/jobs', label: 'Crawl jobs', icon: Workflow },
    ],
  },
  {
    group: 'Knowledge',
    items: [
      { href: '/platform/systems', label: 'Design systems', icon: Boxes },
      { href: '/platform/components', label: 'Components', icon: BookOpen },
      { href: '/platform/storybook', label: 'Storybook & variants', icon: Layers },
      { href: '/platform/tokens', label: 'Tokens', icon: Palette },
      { href: '/platform/guidelines', label: 'Guidelines', icon: ClipboardCheck },
    ],
  },
  {
    group: 'Analysis',
    items: [
      { href: '/platform/compare', label: 'Compare', icon: Columns3 },
      { href: '/platform/reports', label: 'Reports & exports', icon: FileText },
      { href: '/platform/quality', label: 'Data quality', icon: ShieldCheck },
      { href: '/platform/review', label: 'Review queue', icon: BarChart3 },
    ],
  },
]

export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const router = useRouter()
  const isPublicAuth = pathname === '/platform/login'
  const me = useMe()
  const logout = useLogout()
  const { theme, toggleTheme } = useApp()
  const [q, setQ] = useState('')
  const [navOpen, setNavOpen] = useState(false)
  const unauth = me.error instanceof ApiError && me.error.status === 401

  useEffect(() => {
    if (unauth && !isPublicAuth) router.replace(`/platform/login?next=${encodeURIComponent(pathname)}`)
  }, [unauth, isPublicAuth, pathname, router])
  useEffect(() => setNavOpen(false), [pathname])

  if (isPublicAuth) return <div className={s.loginWrap}>{children}</div>

  const user = me.data
  return (
    <div className={s.shell}>
      <aside className={s.side} data-open={navOpen || undefined} aria-label="Platform navigation">
        <Link href="/platform" className={s.brand}>
          <span className={s.mark} aria-hidden>
            <i />
            <i />
            <i />
            <i />
          </span>
          DS <em>Research</em>
        </Link>
        <nav>
          {NAV.map((g) => (
            <div key={g.group} className={s.group}>
              <p>{g.group}</p>
              {g.items.map((it) => {
                const active = 'exact' in it && it.exact ? pathname === it.href : pathname.startsWith(it.href)
                return (
                  <Link key={it.href} href={it.href} aria-current={active ? 'page' : undefined}>
                    <it.icon size={16} aria-hidden />
                    {it.label}
                  </Link>
                )
              })}
            </div>
          ))}
          {isAdmin(user) && (
            <div className={s.group}>
              <p>Administration</p>
              <Link href="/platform/admin" aria-current={pathname.startsWith('/platform/admin') ? 'page' : undefined}>
                <Settings size={16} aria-hidden />
                Settings & account
              </Link>
            </div>
          )}
        </nav>
      </aside>
      {navOpen && <div className={s.scrim} onClick={() => setNavOpen(false)} />}

      <div className={s.main}>
        <header className={s.top}>
          <button className={s.burger} onClick={() => setNavOpen((o) => !o)} aria-label="Toggle navigation" aria-expanded={navOpen}>
            {navOpen ? <X size={18} /> : <Menu size={18} />}
          </button>
          <form
            role="search"
            className={s.search}
            onSubmit={(e) => {
              e.preventDefault()
              if (q.trim()) router.push(`/platform/search?q=${encodeURIComponent(q.trim())}`)
            }}
          >
            <Search size={16} aria-hidden />
            <label htmlFor="global-search" className="sr-only">
              Search the knowledge base
            </label>
            <input id="global-search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search systems, components, tokens, guidelines…" maxLength={200} />
          </form>
          <button className={s.icon} onClick={toggleTheme} aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}>
            {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
          </button>
          <div className={s.user}>
            {user ? (
              <>
                <span>
                  {user.name || user.email}
                  <small>administrator</small>
                </span>
                <button
                  className={s.icon}
                  aria-label="Sign out"
                  onClick={() => logout.mutate(undefined, { onSettled: () => router.replace('/platform/login') })}
                >
                  <LogOut size={16} />
                </button>
              </>
            ) : (
              <Skeleton w={120} h={18} />
            )}
          </div>
        </header>
        <main id="main" className={s.content}>
          {user ? children : unauth ? null : <Skeleton h={300} />}
        </main>
      </div>
    </div>
  )
}
