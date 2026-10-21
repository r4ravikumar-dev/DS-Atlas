'use client'

import { useEffect, useMemo, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Search, X } from 'lucide-react'
import { RESOURCE_GROUPS } from '@/data/resources'
import { Card } from './Card'
import { useApp } from './Providers'
import styles from './ResourceLibrary.module.scss'

const ACCENTS = ['var(--accent)', 'var(--violet)', 'var(--sky)', 'var(--coral)', 'var(--mint)', 'var(--amber)', 'var(--pink)']

export function ResourceLibrary() {
  const [query, setQuery] = useState('')
  const [active, setActive] = useState(RESOURCE_GROUPS[0].id)
  const [source, setSource] = useState<'all' | string>('all')
  const { lenis } = useApp()

  const sources = useMemo(() => Array.from(new Set(RESOURCE_GROUPS.flatMap((g) => g.items.map((i) => i.source).filter(Boolean)))) as string[], [])

  const groups = useMemo(() => {
    const q = query.trim().toLowerCase()
    return RESOURCE_GROUPS.map((g) => ({
      ...g,
      items: g.items.filter(
        (i) =>
          (source === 'all' || i.source === source) &&
          (!q || `${i.name} ${i.desc} ${i.meta ?? ''} ${g.title}`.toLowerCase().includes(q)),
      ),
    })).filter((g) => g.items.length > 0)
  }, [query, source])

  const total = groups.reduce((n, g) => n + g.items.length, 0)

  // Scroll-spy for the sticky index
  useEffect(() => {
    const els = groups.map((g) => document.getElementById(g.id)).filter(Boolean) as HTMLElement[]
    const io = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter((e) => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)
        if (visible[0]) setActive(visible[0].target.id)
      },
      { rootMargin: '-20% 0px -65% 0px' },
    )
    els.forEach((el) => io.observe(el))
    return () => io.disconnect()
  }, [groups])

  const jump = (id: string) => {
    const el = document.getElementById(id)
    if (!el) return
    if (lenis.current) lenis.current.scrollTo(el, { offset: -90 })
    else el.scrollIntoView({ behavior: 'smooth' })
  }

  return (
    <div className={`container ${styles.layout}`}>
      <aside className={styles.side}>
        <label className={styles.search}>
          <Search size={16} />
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Filter library…" aria-label="Filter resources" />
          {query && (
            <button onClick={() => setQuery('')} aria-label="Clear">
              <X size={14} />
            </button>
          )}
        </label>

        <div className={styles.sources} role="group" aria-label="Source">
          {['all', ...sources].map((s) => (
            <button key={s} aria-pressed={source === s} onClick={() => setSource(s)}>
              {s === 'all' ? 'All sources' : s}
            </button>
          ))}
        </div>

        <nav className={styles.toc} aria-label="Library sections">
          {groups.map((g) => (
            <button key={g.id} onClick={() => jump(g.id)} data-active={active === g.id || undefined}>
              {active === g.id && <motion.span layoutId="toc-bar" className={styles.bar} />}
              <span>{g.title}</span>
              <small>{g.items.length}</small>
            </button>
          ))}
        </nav>
        <p className={styles.total}>
          <strong>{total}</strong> resources
        </p>
      </aside>

      <div className={styles.main}>
        <AnimatePresence mode="popLayout">
          {groups.length === 0 && (
            <motion.p key="empty" className={styles.empty} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              Nothing matches “{query}”.
            </motion.p>
          )}
          {groups.map((g) => {
            const accent = ACCENTS[RESOURCE_GROUPS.findIndex((x) => x.id === g.id) % ACCENTS.length]
            return (
              <motion.section
                key={g.id}
                id={g.id}
                layout
                className={styles.group}
                initial={{ opacity: 0, y: 24 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-60px' }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
              >
                <header>
                  <span className="mono" style={{ color: accent }}>
                    {g.kicker}
                  </span>
                  <h2>{g.title}</h2>
                  <p>{g.intro}</p>
                </header>
                <motion.div layout className={styles.grid}>
                  <AnimatePresence mode="popLayout" initial={false}>
                    {g.items.map((r) => (
                      <motion.div
                        key={r.name}
                        layout
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.95 }}
                      >
                        <Card title={r.name} href={r.url} desc={r.desc} meta={r.meta ?? r.source} repo={r.repo} accent={accent} reveal={false} />
                      </motion.div>
                    ))}
                  </AnimatePresence>
                </motion.div>
              </motion.section>
            )
          })}
        </AnimatePresence>
      </div>
    </div>
  )
}
