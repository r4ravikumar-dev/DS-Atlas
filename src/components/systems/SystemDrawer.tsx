'use client'

import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { ArrowUpRight, Layers, Plus, Check, X } from 'lucide-react'
import { CATEGORIES, SYSTEMS, type DesignSystem } from '@/data/systems'
import { FigmaIcon, GithubIcon } from '../Icons'
import { useApp } from '../Providers'
import { CATEGORY_COLOR, SOURCE_LABEL, TOKEN_TAGS, frameworkTags, hasTokens, initials } from './utils'
import styles from './SystemDrawer.module.scss'

interface Props {
  system: DesignSystem | null
  onClose: () => void
  onSelect: (id: string) => void
  comparing: string[]
  onToggleCompare: (id: string) => void
}

export function SystemDrawer({ system, onClose, onSelect, comparing, onToggleCompare }: Props) {
  const { lenis } = useApp()
  const [mounted, setMounted] = useState(false)
  useEffect(() => setMounted(true), [])

  useEffect(() => {
    if (!system) return
    lenis.current?.stop()
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => {
      lenis.current?.start()
      window.removeEventListener('keydown', onKey)
    }
  }, [system, onClose, lenis])

  if (!mounted) return null

  const related = system ? SYSTEMS.filter((s) => s.category === system.category && s.id !== system.id).slice(0, 6) : []
  const selected = system ? comparing.includes(system.id) : false

  return createPortal(
    <AnimatePresence>
      {system && (
        <>
          <motion.div className={styles.scrim} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose} />
          <motion.aside
            key="drawer"
            className={styles.drawer}
            role="dialog"
            aria-modal="true"
            aria-labelledby="drawer-title"
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', stiffness: 260, damping: 32 }}
            data-lenis-prevent
            style={{ '--c': CATEGORY_COLOR[system.category] } as React.CSSProperties}
          >
            <button className={styles.close} onClick={onClose} aria-label="Close details" autoFocus>
              <X size={18} />
            </button>

            <motion.div key={system.id} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay: 0.1 }}>
              <div className={styles.badge}>{initials(system)}</div>
              <p className={styles.company}>
                {system.company} · <span>{CATEGORIES[system.category].label}</span>
              </p>
              <h2 id="drawer-title" className={styles.title}>
                {system.name}
              </h2>
              <p className={styles.strength}>{system.strength}</p>
              {system.why && <p className={styles.why}>{system.why}</p>}

              <div className={styles.actions}>
                <a href={system.url} target="_blank" rel="noopener noreferrer" className={styles.primary}>
                  Open docs <ArrowUpRight size={16} />
                </a>
                {system.repo && (
                  <a href={system.repo} target="_blank" rel="noopener noreferrer" className={styles.secondary}>
                    <GithubIcon size={15} /> Source
                  </a>
                )}
                <button className={styles.secondary} onClick={() => onToggleCompare(system.id)} aria-pressed={selected}>
                  {selected ? <Check size={15} /> : <Plus size={15} />} {selected ? 'Comparing' : 'Compare'}
                </button>
              </div>

              <dl className={styles.facts}>
                <div>
                  <dt>Source</dt>
                  <dd>{SOURCE_LABEL[system.source]}</dd>
                </div>
                <div>
                  <dt>Figma kit</dt>
                  <dd>
                    {system.figma ? (
                      <>
                        <FigmaIcon size={14} /> {system.figma === 'official' ? 'Official' : 'Community'}
                      </>
                    ) : (
                      '—'
                    )}
                  </dd>
                </div>
                <div>
                  <dt>Token pipeline</dt>
                  <dd>{hasTokens(system) ? system.stack.filter((t) => TOKEN_TAGS.includes(t)).join(', ') : '—'}</dd>
                </div>
                <div>
                  <dt>AI readiness</dt>
                  <dd>
                    {system.ai !== undefined ? (
                      <span className={styles.meter} aria-label={`${system.ai} of 5`}>
                        {Array.from({ length: 5 }, (_, i) => (
                          <motion.i
                            key={i}
                            data-on={i < system.ai! || undefined}
                            initial={{ scaleY: 0 }}
                            animate={{ scaleY: 1 }}
                            transition={{ delay: 0.25 + i * 0.06 }}
                          />
                        ))}
                        <span>{system.ai}/5</span>
                      </span>
                    ) : (
                      'Not rated'
                    )}
                  </dd>
                </div>
              </dl>

              {frameworkTags(system).length > 0 && (
                <>
                  <h3 className={styles.sub}>Stack</h3>
                  <ul className={styles.tags}>
                    {frameworkTags(system).map((t) => (
                      <li key={t}>{t}</li>
                    ))}
                  </ul>
                </>
              )}

              {related.length > 0 && (
                <>
                  <h3 className={styles.sub}>
                    <Layers size={14} /> Also in {CATEGORIES[system.category].label}
                  </h3>
                  <ul className={styles.related}>
                    {related.map((r) => (
                      <li key={r.id}>
                        <button onClick={() => onSelect(r.id)}>
                          <span>{r.name}</span>
                          <small>{r.company}</small>
                        </button>
                      </li>
                    ))}
                  </ul>
                </>
              )}
              <p className={styles.note}>AI-readiness and stack tags via designsystems.one where available.</p>
            </motion.div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>,
    document.body,
  )
}
