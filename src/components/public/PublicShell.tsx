'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { Moon, Search, Settings, Sun } from 'lucide-react'
import { isAdmin, useMe } from '@/features/auth/api'
import { useStats } from '@/features/public/api'
import { useApp } from '../Providers'
import { fmtDate } from '../ui'
import s from './PublicShell.module.scss'

const NAV = [
  { href: '/', label: 'Design systems', exact: true },
  { href: '/components', label: 'Components' },
  { href: '/tokens', label: 'Tokens' },
  { href: '/guidelines', label: 'Guidelines' },
  { href: '/patterns', label: 'Patterns' },
  { href: '/storybook', label: 'Storybook' },
  { href: '/compare', label: 'Compare' },
]

/** Header, section navigation and footer of the public directory. No account is needed for anything rendered inside. */
export function PublicShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const router = useRouter()
  const { theme, toggleTheme } = useApp()
  const me = useMe()
  const stats = useStats()
  const [q, setQ] = useState('')
  return (
    <div className={s.wrap}>
      <a href="#main" className={s.skip}>Skip to content</a>
      <header className={s.header}>
        <div className={s.bar}>
          <Link href="/" className={s.brand}>
            <span className={s.mark} aria-hidden><i /><i /><i /><i /></span>
            Design Systems <em>Directory</em>
          </Link>
          <form role="search" className={s.search} onSubmit={(e) => (e.preventDefault(), q.trim() && router.push(`/search?q=${encodeURIComponent(q.trim())}`))}>
            <Search size={15} aria-hidden />
            <label htmlFor="public-search" className="sr-only">Search design systems, components, tokens and guidelines</label>
            <input id="public-search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search systems, components, tokens…" maxLength={200} />
          </form>
          <div className={s.actions}>
            {isAdmin(me.data) && <Link href="/admin" className={s.admin}><Settings size={14} aria-hidden /> Admin</Link>}
            <button className={s.icon} onClick={toggleTheme} aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}>
              {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
            </button>
          </div>
        </div>
        <nav className={s.nav} aria-label="Directory sections">
          {NAV.map((n) => {
            const active = n.exact ? pathname === n.href || pathname.startsWith('/systems') : pathname.startsWith(n.href)
            return <Link key={n.href} href={n.href} aria-current={active ? 'page' : undefined}>{n.label}</Link>
          })}
        </nav>
      </header>
      <main id="main" className={s.main}>{children}</main>
      <footer className={s.footer}>
        <p>
          Collected from public directories and each system&apos;s own documentation, with sources and evidence on every record.
          Links marked verified were confirmed on the official site; others are directory-listed.
        </p>
        <p className={s.muted}>
          {stats.data?.last_sync_at ? `Checked for updates ${fmtDate(stats.data.last_sync_at)}` : ''}
          {stats.data?.last_sync_at && stats.data?.content_updated_at ? ' · ' : ''}
          {stats.data?.content_updated_at ? `content last changed ${fmtDate(stats.data.content_updated_at)}` : ''}
        </p>
      </footer>
    </div>
  )
}
