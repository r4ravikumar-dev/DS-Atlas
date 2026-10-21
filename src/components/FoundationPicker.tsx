'use client'

import { useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import { ArrowUpRight, Trophy } from 'lucide-react'
import { FOUNDATIONS } from '@/data/resources'
import { GithubIcon } from './Icons'
import styles from './FoundationPicker.module.scss'

type Key = 'control' | 'speed' | 'a11y'

const PRIORITIES: { key: Key; label: string; hint: string }[] = [
  { key: 'control', label: 'Design control', hint: 'Own every pixel & token' },
  { key: 'speed', label: 'Speed to ship', hint: 'Pre-styled, ready today' },
  { key: 'a11y', label: 'Accessibility depth', hint: 'ARIA, focus, i18n' },
]

const PRESETS: { label: string; w: Record<Key, number> }[] = [
  { label: 'Custom brand', w: { control: 5, speed: 2, a11y: 4 } },
  { label: 'Internal tool', w: { control: 1, speed: 5, a11y: 2 } },
  { label: 'Public sector', w: { control: 3, speed: 2, a11y: 5 } },
  { label: 'Balanced', w: { control: 3, speed: 3, a11y: 3 } },
]

export function FoundationPicker() {
  const [w, setW] = useState<Record<Key, number>>(PRESETS[0].w)

  const ranked = useMemo(() => {
    const sum = w.control + w.speed + w.a11y || 1
    return FOUNDATIONS.map((f) => ({
      ...f,
      score: Math.round(((f.control * w.control + f.speed * w.speed + f.a11y * w.a11y) / (sum * 5)) * 100),
    })).sort((a, b) => b.score - a.score)
  }, [w])

  return (
    <div className={`container ${styles.wrap}`}>
      <div className={styles.panel} data-reveal>
        <p className="mono">Weight your priorities</p>
        <div className={styles.presets}>
          {PRESETS.map((p) => {
            const on = PRIORITIES.every((k) => p.w[k.key] === w[k.key])
            return (
              <button key={p.label} aria-pressed={on} onClick={() => setW(p.w)}>
                {p.label}
              </button>
            )
          })}
        </div>
        {PRIORITIES.map((p) => (
          <label key={p.key} className={styles.slider}>
            <span className={styles.sLabel}>
              {p.label}
              <small>{p.hint}</small>
            </span>
            <input
              type="range"
              min={0}
              max={5}
              step={1}
              value={w[p.key]}
              onChange={(e) => setW((prev) => ({ ...prev, [p.key]: Number(e.target.value) }))}
              style={{ '--v': `${(w[p.key] / 5) * 100}%` } as React.CSSProperties}
            />
            <output>{w[p.key]}</output>
          </label>
        ))}
      </div>

      <ol className={styles.list}>
        {ranked.map((f, i) => (
          <motion.li key={f.id} id={f.id} layout transition={{ type: 'spring', stiffness: 300, damping: 30 }} className={styles.item} data-top={i === 0 || undefined}>
            <div className={styles.rank}>
              {i === 0 ? <Trophy size={18} /> : <span>{String(i + 1).padStart(2, '0')}</span>}
            </div>
            <div className={styles.info}>
              <div className={styles.titleRow}>
                <h3>{f.name}</h3>
                <span className={styles.tag}>{f.tagline}</span>
              </div>
              <p>{f.desc}</p>
              <dl>
                <div>
                  <dt>Best for</dt>
                  <dd>{f.bestFor}</dd>
                </div>
                <div>
                  <dt>Styling</dt>
                  <dd>{f.styling}</dd>
                </div>
              </dl>
              <div className={styles.links}>
                <a href={f.url} target="_blank" rel="noopener noreferrer">
                  Docs <ArrowUpRight size={14} />
                </a>
                <a href={f.repo} target="_blank" rel="noopener noreferrer">
                  <GithubIcon size={14} /> GitHub
                </a>
              </div>
            </div>
            <div className={styles.scores}>
              <div className={styles.match}>
                <motion.span key={f.score} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}>
                  {f.score}
                </motion.span>
                <small>% match</small>
              </div>
              {PRIORITIES.map((p) => (
                <div key={p.key} className={styles.bar}>
                  <span>{p.label}</span>
                  <i>
                    <motion.b initial={{ width: 0 }} whileInView={{ width: `${(f[p.key] / 5) * 100}%` }} viewport={{ once: true }} transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1] }} />
                  </i>
                </div>
              ))}
            </div>
          </motion.li>
        ))}
      </ol>
    </div>
  )
}
