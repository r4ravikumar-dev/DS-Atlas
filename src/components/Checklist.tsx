'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Check, ChevronDown, Download, Eye, EyeOff, RotateCcw } from 'lucide-react'
import { CHECKLIST, CHECKLIST_TOTAL, type ChecklistCategory, type ChecklistSection } from '@/data/checklist'
import { gsap } from '@/lib/gsap'
import styles from './Checklist.module.scss'

const STORAGE_KEY = 'dsa-checklist-v1'

const countDone = (sections: ChecklistSection[], done: Set<string>) =>
  sections.reduce((n, s) => n + s.items.filter((i) => done.has(i.id)).length, 0)
const countAll = (sections: ChecklistSection[]) => sections.reduce((n, s) => n + s.items.length, 0)

export function Checklist() {
  const [done, setDone] = useState<Set<string>>(new Set())
  const [catId, setCatId] = useState(CHECKLIST[0].id)
  const [hideDone, setHideDone] = useState(false)
  const [loaded, setLoaded] = useState(false)

  // Restore progress + honour ?c=<category> deep links
  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (raw) setDone(new Set(JSON.parse(raw)))
    } catch {}
    const c = new URLSearchParams(window.location.search).get('c')
    if (c && CHECKLIST.some((x) => x.id === c)) setCatId(c)
    setLoaded(true)
  }, [])

  useEffect(() => {
    if (!loaded) return
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify([...done]))
    } catch {}
  }, [done, loaded])

  const toggle = useCallback((ids: string[], value?: boolean) => {
    setDone((prev) => {
      const next = new Set(prev)
      const target = value ?? !ids.every((id) => prev.has(id))
      ids.forEach((id) => (target ? next.add(id) : next.delete(id)))
      return next
    })
  }, [])

  const cat = CHECKLIST.find((c) => c.id === catId)!
  const overall = done.size / CHECKLIST_TOTAL

  const exportMarkdown = () => {
    const lines = ['# Design System Checklist', '', `Progress: ${done.size}/${CHECKLIST_TOTAL}`, '']
    CHECKLIST.forEach((c) => {
      lines.push(`## ${c.title}`, '')
      c.sections.forEach((s) => {
        lines.push(`### ${s.title}`)
        s.items.forEach((i) => lines.push(`- [${done.has(i.id) ? 'x' : ' '}] ${i.title}${i.desc ? ` — ${i.desc}` : ''}`))
        lines.push('')
      })
    })
    const blob = new Blob([lines.join('\n')], { type: 'text/markdown' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = 'design-system-checklist.md'
    a.click()
    URL.revokeObjectURL(a.href)
  }

  const reset = () => {
    if (window.confirm('Clear all checklist progress saved in this browser?')) setDone(new Set())
  }

  return (
    <div className={`container ${styles.wrap}`}>
      {/* Overview */}
      <div className={styles.overview}>
        <div className={styles.overall}>
          <div className={styles.big}>
            <motion.span key={Math.round(overall * 100)} initial={{ y: 10, opacity: 0 }} animate={{ y: 0, opacity: 1 }}>
              {Math.round(overall * 100)}
            </motion.span>
            <small>%</small>
          </div>
          <p>
            {done.size} of {CHECKLIST_TOTAL} checks complete · saved in this browser
          </p>
          <div className={styles.track}>
            <motion.i animate={{ scaleX: overall }} transition={{ type: 'spring', stiffness: 120, damping: 20 }} />
          </div>
        </div>
        <div className={styles.tools}>
          <button onClick={() => setHideDone((h) => !h)} aria-pressed={hideDone}>
            {hideDone ? <EyeOff size={15} /> : <Eye size={15} />} {hideDone ? 'Showing open' : 'Hide completed'}
          </button>
          <button onClick={exportMarkdown}>
            <Download size={15} /> Export .md
          </button>
          <button onClick={reset} className={styles.danger}>
            <RotateCcw size={15} /> Reset
          </button>
        </div>
      </div>

      {/* Category tabs with progress rings */}
      <div className={styles.cats} role="tablist" aria-label="Checklist category">
        {CHECKLIST.map((c, i) => (
          <CategoryTab key={c.id} cat={c} index={i} active={c.id === catId} done={done} onClick={() => setCatId(c.id)} />
        ))}
      </div>

      <AnimatePresence mode="wait">
        <motion.div
          key={cat.id}
          role="tabpanel"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
        >
          <p className={styles.summary}>{cat.summary}</p>
          <div className={cat.id === 'components' ? styles.sectionsDense : styles.sections}>
            {cat.sections.map((s) => (
              <SectionCard key={s.id} section={s} done={done} hideDone={hideDone} onToggle={toggle} dense={cat.id === 'components'} />
            ))}
          </div>
        </motion.div>
      </AnimatePresence>

      <p className={styles.credit}>
        Adapted from the open-source{' '}
        <a href="https://github.com/ardakaracizmeli/design-system-checklist" target="_blank" rel="noopener noreferrer">
          Design System Checklist
        </a>{' '}
        (
        <a href="https://www.designsystemchecklist.com" target="_blank" rel="noopener noreferrer">
          designsystemchecklist.com
        </a>
        ).
      </p>
    </div>
  )
}

function Ring({ value, size = 44 }: { value: number; size?: number }) {
  const r = (size - 6) / 2
  const c = 2 * Math.PI * r
  return (
    <svg width={size} height={size} className={styles.ring} aria-hidden>
      <circle cx={size / 2} cy={size / 2} r={r} strokeWidth={3} className={styles.ringBg} />
      <motion.circle
        cx={size / 2}
        cy={size / 2}
        r={r}
        strokeWidth={3}
        strokeLinecap="round"
        strokeDasharray={c}
        animate={{ strokeDashoffset: c * (1 - value) }}
        transition={{ type: 'spring', stiffness: 90, damping: 18 }}
        className={styles.ringFg}
      />
    </svg>
  )
}

function CategoryTab({
  cat,
  index,
  active,
  done,
  onClick,
}: {
  cat: ChecklistCategory
  index: number
  active: boolean
  done: Set<string>
  onClick: () => void
}) {
  const all = countAll(cat.sections)
  const d = countDone(cat.sections, done)
  return (
    <button role="tab" aria-selected={active} className={styles.cat} onClick={onClick}>
      {active && <motion.span layoutId="check-cat" className={styles.catBg} />}
      <Ring value={all ? d / all : 0} />
      <span className={styles.catText}>
        <small>0{index + 1}</small>
        <strong>{cat.title}</strong>
        <em>
          {d}/{all}
        </em>
      </span>
    </button>
  )
}

function SectionCard({
  section,
  done,
  hideDone,
  onToggle,
  dense,
}: {
  section: ChecklistSection
  done: Set<string>
  hideDone: boolean
  onToggle: (ids: string[], value?: boolean) => void
  dense: boolean
}) {
  const [open, setOpen] = useState(true)
  const ref = useRef<HTMLElement>(null)
  const ids = useMemo(() => section.items.map((i) => i.id), [section])
  const d = ids.filter((id) => done.has(id)).length
  const complete = d === ids.length
  const prevComplete = useRef(complete)

  // GSAP particle burst when a section flips to complete
  useEffect(() => {
    if (complete && !prevComplete.current && ref.current && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      const host = ref.current
      const colors = ['var(--accent)', 'var(--violet)', 'var(--mint)', 'var(--coral)', 'var(--sky)']
      for (let i = 0; i < 18; i++) {
        const p = document.createElement('span')
        p.className = styles.particle
        p.style.background = colors[i % colors.length]
        host.appendChild(p)
        const angle = (Math.PI * 2 * i) / 18
        gsap.fromTo(
          p,
          { x: 0, y: 0, scale: 1, opacity: 1 },
          {
            x: Math.cos(angle) * gsap.utils.random(50, 110),
            y: Math.sin(angle) * gsap.utils.random(40, 90),
            scale: 0,
            opacity: 0,
            duration: gsap.utils.random(0.6, 1),
            ease: 'power3.out',
            onComplete: () => p.remove(),
          },
        )
      }
      gsap.fromTo(host, { scale: 0.98 }, { scale: 1, duration: 0.6, ease: 'elastic.out(1, 0.4)' })
    }
    prevComplete.current = complete
  }, [complete])

  const visible = hideDone ? section.items.filter((i) => !done.has(i.id)) : section.items
  if (hideDone && complete) return null

  return (
    <motion.section ref={ref} id={section.id} layout className={styles.section} data-complete={complete || undefined}>
      <header>
        <button className={styles.head} onClick={() => setOpen((o) => !o)} aria-expanded={open}>
          <span className={styles.secTitle}>{section.title}</span>
          <span className={styles.secCount}>
            {d}/{ids.length}
          </span>
          <motion.span animate={{ rotate: open ? 0 : -90 }} className={styles.chev}>
            <ChevronDown size={16} />
          </motion.span>
        </button>
        <button className={styles.all} onClick={() => onToggle(ids)}>
          {complete ? 'Clear' : 'Check all'}
        </button>
      </header>
      <div className={styles.secBar}>
        <motion.i animate={{ scaleX: ids.length ? d / ids.length : 0 }} />
      </div>
      <AnimatePresence initial={false}>
        {open && (
          <motion.ul
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
            className={dense ? styles.itemsDense : styles.items}
          >
            <AnimatePresence initial={false}>
              {visible.map((item) => {
                const checked = done.has(item.id)
                return (
                  <motion.li key={item.id} layout exit={{ opacity: 0, height: 0 }}>
                    <label className={styles.item} data-checked={checked || undefined}>
                      <input type="checkbox" checked={checked} onChange={() => onToggle([item.id])} />
                      <span className={styles.box}>
                        <AnimatePresence>
                          {checked && (
                            <motion.span initial={{ scale: 0, rotate: -45 }} animate={{ scale: 1, rotate: 0 }} exit={{ scale: 0 }}>
                              <Check size={13} strokeWidth={3} />
                            </motion.span>
                          )}
                        </AnimatePresence>
                      </span>
                      <span className={styles.itemText}>
                        <strong>{item.title}</strong>
                        {item.desc && <small>{item.desc}</small>}
                      </span>
                    </label>
                  </motion.li>
                )
              })}
            </AnimatePresence>
          </motion.ul>
        )}
      </AnimatePresence>
    </motion.section>
  )
}
