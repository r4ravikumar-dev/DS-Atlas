'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import Fuse from 'fuse.js'
import { AnimatePresence, motion } from 'framer-motion'
import { ArrowUpRight, CornerDownLeft, Search } from 'lucide-react'
import { buildIndex, PAGES, type SearchEntry } from '@/lib/search'
import { useApp } from './Providers'
import styles from './CommandPalette.module.scss'

const KIND_COLOR: Record<SearchEntry['kind'], string> = {
  Page: 'var(--accent)',
  System: 'var(--violet)',
  Directory: 'var(--sky)',
  Repo: 'var(--mint)',
  Resource: 'var(--amber)',
  Foundation: 'var(--coral)',
  Checklist: 'var(--pink)',
}

export function CommandPalette() {
  const { paletteOpen, setPaletteOpen } = useApp()
  const router = useRouter()
  const pathname = usePathname()
  const [query, setQuery] = useState('')
  const [active, setActive] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const listRef = useRef<HTMLUListElement>(null)

  const index = useMemo(() => buildIndex(), [])
  const fuse = useMemo(
    () =>
      new Fuse(index, {
        keys: [
          { name: 'title', weight: 3 },
          { name: 'subtitle', weight: 1 },
          { name: 'keywords', weight: 1 },
        ],
        threshold: 0.36,
        ignoreLocation: true,
      }),
    [index],
  )

  const results = useMemo(() => {
    if (!query.trim()) return PAGES
    return fuse.search(query, { limit: 40 }).map((r) => r.item)
  }, [query, fuse])

  useEffect(() => {
    if (paletteOpen) {
      setQuery('')
      setActive(0)
      requestAnimationFrame(() => inputRef.current?.focus())
    }
  }, [paletteOpen])

  useEffect(() => setActive(0), [query])

  useEffect(() => {
    listRef.current?.querySelector(`[data-index="${active}"]`)?.scrollIntoView({ block: 'nearest' })
  }, [active])

  const open = (entry: SearchEntry) => {
    setPaletteOpen(false)
    if (entry.external) {
      window.open(entry.href, '_blank', 'noopener,noreferrer')
      return
    }
    const [path, hash] = entry.href.split('#')
    // Same page + hash: set location.hash so in-page listeners (drawer, scroll) react.
    if (hash && path === pathname) window.location.hash = hash
    else router.push(entry.href)
  }

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActive((a) => Math.min(a + 1, results.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActive((a) => Math.max(a - 1, 0))
    } else if (e.key === 'Enter' && results[active]) {
      e.preventDefault()
      open(results[active])
    } else if (e.key === 'Escape') {
      setPaletteOpen(false)
    }
  }

  return (
    <AnimatePresence>
      {paletteOpen && (
        <motion.div
          className={styles.overlay}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          onMouseDown={(e) => e.target === e.currentTarget && setPaletteOpen(false)}
        >
          <motion.div
            className={styles.panel}
            role="dialog"
            aria-modal="true"
            aria-label="Search the atlas"
            initial={{ opacity: 0, y: -24, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -12, scale: 0.98 }}
            onKeyDown={onKeyDown}
          >
            <div className={styles.field}>
              <Search size={18} />
              <input
                ref={inputRef}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search systems, tools, repos, checklist…"
                aria-label="Search"
                role="combobox"
                aria-expanded="true"
                aria-controls="palette-results"
                aria-activedescendant={results[active] ? `opt-${results[active].id}` : undefined}
              />
              <kbd>esc</kbd>
            </div>

            <ul ref={listRef} id="palette-results" role="listbox" className={styles.list} data-lenis-prevent>
              {results.length === 0 && <li className={styles.empty}>No matches for “{query}”.</li>}
              {results.map((r, i) => (
                <li
                  key={r.id}
                  id={`opt-${r.id}`}
                  role="option"
                  aria-selected={i === active}
                  data-index={i}
                  className={styles.item}
                  onMouseMove={() => setActive(i)}
                  onClick={() => open(r)}
                >
                  {i === active && <motion.span layoutId="palette-active" className={styles.hl} transition={{ duration: 0.15 }} />}
                  <span className={styles.kind} style={{ '--c': KIND_COLOR[r.kind] } as React.CSSProperties}>
                    {r.kind}
                  </span>
                  <span className={styles.text}>
                    <strong>{r.title}</strong>
                    <small>{r.subtitle}</small>
                  </span>
                  {r.external ? <ArrowUpRight size={16} className={styles.go} /> : <CornerDownLeft size={14} className={styles.go} />}
                </li>
              ))}
            </ul>
            <footer className={styles.foot}>
              <span>
                <kbd>↑</kbd>
                <kbd>↓</kbd> navigate
              </span>
              <span>
                <kbd>↵</kbd> open
              </span>
              <span className={styles.count}>{index.length} entries indexed</span>
            </footer>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
