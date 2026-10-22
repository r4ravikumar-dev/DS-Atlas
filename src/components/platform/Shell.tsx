'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { BarChart3, BookOpen, Boxes, ClipboardCheck, Columns3, Database, FileText, Gauge, Layers, LogOut, Menu, Moon, Palette, PlusCircle, RefreshCw, Search, Settings, ShieldCheck, Sun, Workflow, X } from 'lucide-react'
import { ApiError } from '@/lib/api/client'
import { isAdmin, useLogout, useMe } from '@/features/auth/api'
import { useApp } from '../Providers'
import { Skeleton } from '../ui'
import s from './Shell.module.scss'

const NAV = [
  { group: 'Overview', items: [{ href: '/admin', label: 'Dashboard', icon: Gauge, exact: true }, { href: '/admin/sync', label: 'Daily sync', icon: RefreshCw }] },
  {
    group: 'Collection',
    items: [
      { href: '/admin/add', label: 'Add source', icon: PlusCircle },
      { href: '/admin/sources', label: 'Sources', icon: Database },
      { href: '/admin/jobs', label: 'Crawl jobs', icon: Workflow },
    ],
  },
  {
    group: 'Data',
    items: [
      { href: '/admin/systems', label: 'Systems (manage)', icon: Boxes },
      { href: '/admin/quality', label: 'Data quality', icon: ShieldCheck },
      { href: '/admin/review', label: 'Review queue', icon: BarChart3 },
      { href: '/admin/reports', label: 'Reports & exports', icon: FileText },
    ],
  },
  {
    group: 'Public directory',
    items: [
      { href: '/systems', label: 'Design systems', icon: Boxes },
      { href: '/components', label: 'Components', icon: BookOpen },
      { href: '/storybook', label: 'Storybook', icon: Layers },
      { href: '/tokens', label: 'Tokens', icon: Palette },
      { href: '/guidelines', label: 'Guidelines', icon: ClipboardCheck },
      { href: '/compare', label: 'Compare', icon: Columns3 },
    ],
  },
]

export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const router = useRouter()
  const isPublicAuth = pathname === '/admin/login'
  const me = useMe()
  const logout = useLogout()
  const { theme, toggleTheme } = useApp()
  const [q, setQ] = useState('')
  const [navOpen, setNavOpen] = useState(false)
  const unauth = me.error instanceof ApiError && me.error.status === 401

  useEffect(() => {
    if (unauth && !isPublicAuth) router.replace(`/admin/login?next=${encodeURIComponent(pathname)}`)
  }, [unauth, isPublicAuth, pathname, router])
  useEffect(() => setNavOpen(false), [pathname])

  if (isPublicAuth) return <div className={s.loginWrap}>{children}</div>

  const user = me.data
  return (
    <div className={s.shell}>
      <aside className={s.side} data-open={navOpen || undefined} aria-label="Platform navigation">
        <Link href="/admin" className={s.brand} aria-label="Administration home">
          <span className={s.mark} aria-hidden>
            <i />
            <i />
            <i />
            <i />
          </span>
          DS <em>Admin</em>
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
              <Link href="/admin/settings" aria-current={pathname.startsWith('/admin/settings') ? 'page' : undefined}>
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
              if (q.trim()) router.push(`/search?q=${encodeURIComponent(q.trim())}`)
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
                  onClick={() => logout.mutate(undefined, { onSettled: () => router.replace('/admin/login') })}
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
