'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { AnimatePresence, LayoutGroup, motion } from 'framer-motion'
import { ArrowUpRight, ChevronDown, LayoutGrid, List, Plus, Check, RotateCcw, Search, X } from 'lucide-react'
import { ALL_STACKS, CATEGORIES, SYSTEMS, type Category, type DesignSystem } from '@/data/systems'
import { FigmaIcon, GithubIcon } from '../Icons'
import { SystemDrawer } from './SystemDrawer'
import { CompareTray } from './CompareTray'
import { CATEGORY_COLOR, SOURCE_LABEL, TOKEN_TAGS, frameworkTags, hasTokens, initials } from './utils'
import styles from './SystemsExplorer.module.scss'

type Sort = 'featured' | 'az' | 'ai'
type Toggle = 'open' | 'repo' | 'figma' | 'tokens' | 'featured'

const TOGGLES: { id: Toggle; label: string; test: (s: DesignSystem) => boolean }[] = [
  { id: 'featured', label: 'Curated benchmark', test: (s) => !!s.featured },
  { id: 'open', label: 'Open source', test: (s) => s.source === 'open' },
  { id: 'repo', label: 'Has repo', test: (s) => !!s.repo },
  { id: 'figma', label: 'Official Figma kit', test: (s) => s.figma === 'official' },
  { id: 'tokens', label: 'Token pipeline', test: hasTokens },
]

const FRAMEWORKS = ALL_STACKS.filter((t) => !TOKEN_TAGS.includes(t))
const CAT_KEYS = Object.keys(CATEGORIES) as Category[]

export function SystemsExplorer() {
  const [query, setQuery] = useState('')
  const [cat, setCat] = useState<Category | 'all'>('all')
  const [toggles, setToggles] = useState<Set<Toggle>>(new Set())
  const [stacks, setStacks] = useState<Set<string>>(new Set())
  const [sort, setSort] = useState<Sort>('featured')
  const [view, setView] = useState<'grid' | 'table'>('grid')
  const [stackOpen, setStackOpen] = useState(false)
  const [openId, setOpenId] = useState<string | null>(null)
  const [comparing, setComparing] = useState<string[]>([])
  const searchRef = useRef<HTMLInputElement>(null)
  const stackRef = useRef<HTMLDivElement>(null)

  // Deep-link: #carbon opens the drawer
  useEffect(() => {
    const sync = () => {
      const id = window.location.hash.slice(1)
      setOpenId(SYSTEMS.some((s) => s.id === id) ? id : null)
    }
    sync()
    window.addEventListener('hashchange', sync)
    return () => window.removeEventListener('hashchange', sync)
  }, [])

  useEffect(() => {
    const close = (e: MouseEvent) => {
      if (stackRef.current && !stackRef.current.contains(e.target as Node)) setStackOpen(false)
    }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [])

  const openSystem = useCallback((id: string | null) => {
    setOpenId(id)
    const url = id ? `#${id}` : window.location.pathname + window.location.search
    history.replaceState(null, '', url)
  }, [])

  const toggleCompare = useCallback((id: string) => {
    setComparing((c) => (c.includes(id) ? c.filter((x) => x !== id) : c.length >= 4 ? c : [...c, id]))
  }, [])

  const flip = <T,>(set: Set<T>, v: T) => {
    const next = new Set(set)
    if (next.has(v)) next.delete(v)
    else next.add(v)
    return next
  }

  const base = useMemo(() => {
    const q = query.trim().toLowerCase()
    return SYSTEMS.filter((s) => {
      if (q && !`${s.name} ${s.company} ${s.strength} ${s.why ?? ''} ${s.stack.join(' ')}`.toLowerCase().includes(q)) return false
      for (const t of TOGGLES) if (toggles.has(t.id) && !t.test(s)) return false
      for (const st of stacks) if (!s.stack.includes(st)) return false
      return true
    })
  }, [query, toggles, stacks])

  const counts = useMemo(() => {
    const c = { all: base.length } as Record<Category | 'all', number>
    CAT_KEYS.forEach((k) => (c[k] = base.filter((s) => s.category === k).length))
    return c
  }, [base])

  const results = useMemo(() => {
    const list = cat === 'all' ? base : base.filter((s) => s.category === cat)
    return [...list].sort((a, b) => {
      if (sort === 'az') return a.name.localeCompare(b.name)
      if (sort === 'ai') return (b.ai ?? -1) - (a.ai ?? -1) || a.name.localeCompare(b.name)
      return Number(!!b.featured) - Number(!!a.featured) || a.name.localeCompare(b.name)
    })
  }, [base, cat, sort])

  const activeFilters = toggles.size + stacks.size + (query ? 1 : 0) + (cat !== 'all' ? 1 : 0)
  const reset = () => {
    setQuery('')
    setCat('all')
    setToggles(new Set())
    setStacks(new Set())
  }

  const current = SYSTEMS.find((s) => s.id === openId) ?? null

  return (
    <section className={`container ${styles.wrap}`}>
      {/* ───── Controls ───── */}
      <div className={styles.controls}>
        <div className={styles.searchRow}>
          <label className={styles.search}>
            <Search size={18} />
            <input
              ref={searchRef}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search by name, company, strength or stack…"
              aria-label="Filter systems"
            />
            {query && (
              <button onClick={() => setQuery('')} aria-label="Clear search">
                <X size={16} />
              </button>
            )}
          </label>

          <div className={styles.stackPicker} ref={stackRef}>
            <button className={styles.select} onClick={() => setStackOpen((o) => !o)} aria-expanded={stackOpen}>
              Stack {stacks.size > 0 && <span className={styles.count}>{stacks.size}</span>}
              <ChevronDown size={16} />
            </button>
            <AnimatePresence>
              {stackOpen && (
                <motion.div
                  className={styles.menu}
                  initial={{ opacity: 0, y: -6, scale: 0.98 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -6, scale: 0.98 }}
                  transition={{ duration: 0.18 }}
                >
                  {FRAMEWORKS.map((f) => (
                    <label key={f} className={styles.option}>
                      <input type="checkbox" checked={stacks.has(f)} onChange={() => setStacks((s) => flip(s, f))} />
                      <span>{f}</span>
                      <small>{SYSTEMS.filter((s) => s.stack.includes(f)).length}</small>
                    </label>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          <label className={styles.selectWrap}>
            <span className="sr-only">Sort</span>
            <select value={sort} onChange={(e) => setSort(e.target.value as Sort)} className={styles.select}>
              <option value="featured">Curated first</option>
              <option value="az">A → Z</option>
              <option value="ai">AI readiness</option>
            </select>
            <ChevronDown size={16} />
          </label>

          <div className={styles.view} role="group" aria-label="View">
            {(['grid', 'table'] as const).map((v) => (
              <button key={v} onClick={() => setView(v)} aria-pressed={view === v} aria-label={`${v} view`}>
                {view === v && <motion.span layoutId="view-pill" className={styles.viewPill} />}
                {v === 'grid' ? <LayoutGrid size={16} /> : <List size={16} />}
              </button>
            ))}
          </div>
        </div>

        <LayoutGroup id="cats">
          <div className={styles.cats} role="tablist" aria-label="Category">
            {(['all', ...CAT_KEYS] as const).map((k) => (
              <button
                key={k}
                role="tab"
                aria-selected={cat === k}
                className={styles.cat}
                onClick={() => setCat(k)}
                style={{ '--c': k === 'all' ? 'var(--text)' : CATEGORY_COLOR[k] } as React.CSSProperties}
              >
                {cat === k && <motion.span layoutId="cat-pill" className={styles.catPill} />}
                <span className={styles.catLabel}>
                  {k === 'all' ? 'All' : CATEGORIES[k].label}
                  <motion.small key={counts[k]} initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }}>
                    {counts[k]}
                  </motion.small>
                </span>
              </button>
            ))}
          </div>
        </LayoutGroup>

        <div className={styles.toggles}>
          {TOGGLES.map((t) => (
            <button key={t.id} className={styles.toggle} aria-pressed={toggles.has(t.id)} onClick={() => setToggles((s) => flip(s, t.id))}>
              <span className={styles.box}>{toggles.has(t.id) && <Check size={12} strokeWidth={3} />}</span>
              {t.label}
            </button>
          ))}
          <AnimatePresence>
            {activeFilters > 0 && (
              <motion.button
                className={styles.reset}
                onClick={reset}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -8 }}
              >
                <RotateCcw size={14} /> Reset ({activeFilters})
              </motion.button>
            )}
          </AnimatePresence>
          <p className={styles.total} aria-live="polite">
            <motion.strong key={results.length} initial={{ y: 8, opacity: 0 }} animate={{ y: 0, opacity: 1 }}>
              {results.length}
            </motion.strong>{' '}
            / {SYSTEMS.length} systems
          </p>
        </div>
      </div>

      {/* ───── Results ───── */}
      {results.length === 0 ? (
        <motion.div className={styles.empty} initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          <p>No systems match those filters.</p>
          <button onClick={reset}>Reset filters</button>
        </motion.div>
      ) : view === 'grid' ? (
        <motion.ul layout className={styles.grid}>
          <AnimatePresence mode="popLayout" initial={false}>
            {results.map((s) => (
              <SystemCard
                key={s.id}
                system={s}
                onOpen={() => openSystem(s.id)}
                comparing={comparing.includes(s.id)}
                onCompare={() => toggleCompare(s.id)}
              />
            ))}
          </AnimatePresence>
        </motion.ul>
      ) : (
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>System</th>
                <th>Category</th>
                <th>Core strength</th>
                <th>Stack</th>
                <th>Source</th>
                <th>Links</th>
              </tr>
            </thead>
            <tbody>
              {results.map((s, i) => (
                <motion.tr
                  key={s.id}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1, transition: { delay: Math.min(i * 0.015, 0.4) } }}
                  onClick={() => openSystem(s.id)}
                >
                  <td>
                    <strong>{s.name}</strong>
                    <small>{s.company}</small>
                  </td>
                  <td>
                    <span className={styles.dot} style={{ background: CATEGORY_COLOR[s.category] }} />
                    {CATEGORIES[s.category].label}
                  </td>
                  <td>{s.strength}</td>
                  <td className={styles.stackCell}>{s.stack.join(', ') || '—'}</td>
                  <td>{SOURCE_LABEL[s.source]}</td>
                  <td className={styles.links} onClick={(e) => e.stopPropagation()}>
                    <a href={s.url} target="_blank" rel="noopener noreferrer" aria-label={`${s.name} docs`}>
                      <ArrowUpRight size={16} />
                    </a>
                    {s.repo && (
                      <a href={s.repo} target="_blank" rel="noopener noreferrer" aria-label={`${s.name} source`}>
                        <GithubIcon size={15} />
                      </a>
                    )}
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <SystemDrawer system={current} onClose={() => openSystem(null)} onSelect={openSystem} comparing={comparing} onToggleCompare={toggleCompare} />
      <CompareTray ids={comparing} onRemove={toggleCompare} onClear={() => setComparing([])} />
    </section>
  )
}

function SystemCard({
  system: s,
  onOpen,
  comparing,
  onCompare,
}: {
  system: DesignSystem
  onOpen: () => void
  comparing: boolean
  onCompare: () => void
}) {
  const ref = useRef<HTMLLIElement>(null)
  const onMove = (e: React.PointerEvent) => {
    const el = ref.current
    if (!el) return
    const r = el.getBoundingClientRect()
    el.style.setProperty('--mx', `${e.clientX - r.left}px`)
    el.style.setProperty('--my', `${e.clientY - r.top}px`)
  }

  return (
    <motion.li
      ref={ref}
      layout
      className={styles.card}
      data-comparing={comparing || undefined}
      style={{ '--c': CATEGORY_COLOR[s.category] } as React.CSSProperties}
      initial={{ opacity: 0, scale: 0.94 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.94, transition: { duration: 0.15 } }}
      transition={{ type: 'spring', stiffness: 400, damping: 36 }}
      onPointerMove={onMove}
    >
      <button className={styles.cardMain} onClick={onOpen} aria-label={`${s.company} ${s.name} — details`}>
        <span className={styles.cardTop}>
          <span className={styles.avatar}>{initials(s)}</span>
          {s.featured && <span className={styles.star}>Curated</span>}
        </span>
        <span className={styles.company}>{s.company}</span>
        <span className={styles.name}>{s.name}</span>
        <span className={styles.strength}>{s.strength}</span>
        <span className={styles.tags}>
          {frameworkTags(s)
            .slice(0, 3)
            .map((t) => (
              <i key={t}>{t}</i>
            ))}
          {hasTokens(s) && <i data-token>Tokens</i>}
        </span>
      </button>
      <span className={styles.cardFoot}>
        <span className={styles.meta}>
          {SOURCE_LABEL[s.source]}
          {s.figma === 'official' && <FigmaIcon size={13} />}
        </span>
        <span className={styles.cardActions}>
          {s.repo && (
            <a href={s.repo} target="_blank" rel="noopener noreferrer" aria-label={`${s.name} source code`}>
              <GithubIcon size={14} />
            </a>
          )}
          <a href={s.url} target="_blank" rel="noopener noreferrer" aria-label={`${s.name} documentation`}>
            <ArrowUpRight size={15} />
          </a>
          <button onClick={onCompare} aria-pressed={comparing} aria-label={comparing ? 'Remove from compare' : 'Add to compare'}>
            {comparing ? <Check size={14} /> : <Plus size={14} />}
          </button>
        </span>
      </span>
    </motion.li>
  )
}
