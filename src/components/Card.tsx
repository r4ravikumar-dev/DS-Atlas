'use client'

import { useRef } from 'react'
import { ArrowUpRight } from 'lucide-react'
import { GithubIcon } from './Icons'
import styles from './Card.module.scss'

interface Props {
  title: string
  href: string
  desc: string
  meta?: string
  repo?: string
  index?: number
  accent?: string
  reveal?: boolean
}

/** External resource card with a pointer-tracking spotlight. */
export function Card({ title, href, desc, meta, repo, index, accent, reveal = true }: Props) {
  const ref = useRef<HTMLElement>(null)

  const onMove = (e: React.PointerEvent) => {
    const el = ref.current
    if (!el) return
    const r = el.getBoundingClientRect()
    el.style.setProperty('--mx', `${e.clientX - r.left}px`)
    el.style.setProperty('--my', `${e.clientY - r.top}px`)
  }

  return (
    <article
      ref={ref}
      className={styles.card}
      onPointerMove={onMove}
      data-reveal={reveal || undefined}
      style={accent ? ({ '--card-accent': accent } as React.CSSProperties) : undefined}
    >
      <a href={href} target="_blank" rel="noopener noreferrer" className={styles.cover} aria-label={`${title} (opens in new tab)`} />
      <header className={styles.top}>
        {index !== undefined && <span className={styles.num}>{String(index + 1).padStart(2, '0')}</span>}
        {meta && <span className={styles.meta}>{meta}</span>}
        <ArrowUpRight className={styles.arrow} size={18} />
      </header>
      <h3 className={styles.title}>{title}</h3>
      <p className={styles.desc}>{desc}</p>
      {repo && (
        <a href={repo} target="_blank" rel="noopener noreferrer" className={styles.repo}>
          <GithubIcon size={14} /> Source
        </a>
      )}
    </article>
  )
}
