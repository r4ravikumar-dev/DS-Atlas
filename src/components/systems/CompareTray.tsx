'use client'

import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { ArrowUpRight, Columns3, X } from 'lucide-react'
import { CATEGORIES, SYSTEMS } from '@/data/systems'
import { useApp } from '../Providers'
import { CATEGORY_COLOR, SOURCE_LABEL, TOKEN_TAGS, frameworkTags, initials } from './utils'
import styles from './CompareTray.module.scss'

interface Props {
  ids: string[]
  onRemove: (id: string) => void
  onClear: () => void
}

export function CompareTray({ ids, onRemove, onClear }: Props) {
  const [open, setOpen] = useState(false)
  const [mounted, setMounted] = useState(false)
  const { lenis } = useApp()
  const list = ids.map((id) => SYSTEMS.find((s) => s.id === id)!).filter(Boolean)

  useEffect(() => setMounted(true), [])
  useEffect(() => {
    if (list.length < 2) setOpen(false)
  }, [list.length])
  useEffect(() => {
    if (!open) return
    lenis.current?.stop()
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false)
    window.addEventListener('keydown', onKey)
    return () => {
      lenis.current?.start()
      window.removeEventListener('keydown', onKey)
    }
  }, [open, lenis])

  if (!mounted) return null

  const rows: { label: string; get: (s: (typeof list)[number]) => React.ReactNode }[] = [
    { label: 'Category', get: (s) => CATEGORIES[s.category].label },
    { label: 'Core strength', get: (s) => s.strength },
    { label: 'Why study it', get: (s) => s.why ?? '—' },
    { label: 'Stack', get: (s) => frameworkTags(s).join(', ') || '—' },
    { label: 'Tokens', get: (s) => s.stack.filter((t) => TOKEN_TAGS.includes(t)).join(', ') || '—' },
    { label: 'Source', get: (s) => SOURCE_LABEL[s.source] },
    { label: 'Figma kit', get: (s) => (s.figma ? (s.figma === 'official' ? 'Official' : 'Community') : '—') },
    { label: 'AI readiness', get: (s) => (s.ai !== undefined ? `${s.ai} / 5` : 'Not rated') },
  ]

  return createPortal(
    <>
      <AnimatePresence>
        {list.length > 0 && (
          <motion.div
            className={styles.tray}
            initial={{ y: 120, x: '-50%', opacity: 0 }}
            animate={{ y: 0, x: '-50%', opacity: 1 }}
            exit={{ y: 120, x: '-50%', opacity: 0 }}
          >
            <span className={styles.label}>Compare</span>
            <ul>
              <AnimatePresence initial={false}>
                {list.map((s) => (
                  <motion.li
                    key={s.id}
                    layout
                    initial={{ opacity: 0, scale: 0.6 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.6 }}
                    style={{ '--c': CATEGORY_COLOR[s.category] } as React.CSSProperties}
                  >
                    <span>{initials(s)}</span>
                    {s.name}
                    <button onClick={() => onRemove(s.id)} aria-label={`Remove ${s.name}`}>
                      <X size={12} />
                    </button>
                  </motion.li>
                ))}
              </AnimatePresence>
            </ul>
            <button className={styles.go} disabled={list.length < 2} onClick={() => setOpen(true)}>
              <Columns3 size={15} /> {list.length < 2 ? 'Pick 2–4' : `Compare ${list.length}`}
            </button>
            <button className={styles.clear} onClick={onClear} aria-label="Clear comparison">
              <X size={16} />
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {open && (
          <motion.div
            className={styles.overlay}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0, pointerEvents: 'none' }}
            onClick={() => setOpen(false)}
          >
            <motion.div
              className={styles.modal}
              role="dialog"
              aria-modal="true"
              aria-label="Compare design systems"
              initial={{ y: 40, opacity: 0, scale: 0.98 }}
              animate={{ y: 0, opacity: 1, scale: 1 }}
              exit={{ y: 40, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              data-lenis-prevent
            >
              <header>
                <h2>Side-by-side</h2>
                <button onClick={() => setOpen(false)} aria-label="Close">
                  <X size={18} />
                </button>
              </header>
              <div className={styles.scroll}>
                <table style={{ '--cols': list.length } as React.CSSProperties}>
                  <thead>
                    <tr>
                      <th />
                      {list.map((s) => (
                        <th key={s.id} style={{ '--c': CATEGORY_COLOR[s.category] } as React.CSSProperties}>
                          <small>{s.company}</small>
                          <span>{s.name}</span>
                          <a href={s.url} target="_blank" rel="noopener noreferrer">
                            Docs <ArrowUpRight size={12} />
                          </a>
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((r) => (
                      <tr key={r.label}>
                        <th scope="row">{r.label}</th>
                        {list.map((s) => (
                          <td key={s.id}>{r.get(s)}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>,
    document.body,
  )
}
