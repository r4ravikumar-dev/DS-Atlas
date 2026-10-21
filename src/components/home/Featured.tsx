'use client'

import { useState } from 'react'
import Link from 'next/link'
import { AnimatePresence, motion } from 'framer-motion'
import { ArrowUpRight } from 'lucide-react'
import { CATEGORIES, SYSTEMS, type Category } from '@/data/systems'
import styles from './Featured.module.scss'

const TABS: Category[] = ['enterprise', 'saas', 'consumer', 'platform', 'public', 'library']

export function Featured() {
  const [tab, setTab] = useState<Category>('enterprise')
  const list = SYSTEMS.filter((s) => s.featured && s.category === tab)

  return (
    <section className={`container ${styles.section}`} aria-labelledby="featured-title">
      <div className={styles.head} data-reveal>
        <div>
          <p className="mono">The benchmark shortlist</p>
          <h2 id="featured-title">
            Study the system that matches your <span className="serif">product</span>.
          </h2>
        </div>
        <Link href="/systems" className={styles.all}>
          All {SYSTEMS.length} systems <ArrowUpRight size={16} />
        </Link>
      </div>

      <div className={styles.tabs} role="tablist" data-reveal>
        {TABS.map((t) => (
          <button key={t} role="tab" aria-selected={tab === t} className={styles.tab} onClick={() => setTab(t)}>
            {tab === t && <motion.span layoutId="featured-tab" className={styles.tabBg} />}
            <span>{CATEGORIES[t].label}</span>
          </button>
        ))}
      </div>

      <motion.div layout className={styles.grid} role="tabpanel">
        <AnimatePresence mode="popLayout" initial={false}>
          {list.map((s, i) => (
            <motion.article
              key={s.id}
              layout
              className={styles.item}
              initial={{ opacity: 0, y: 30, filter: 'blur(6px)' }}
              animate={{ opacity: 1, y: 0, filter: 'blur(0px)', transition: { delay: i * 0.05, duration: 0.5, ease: [0.22, 1, 0.36, 1] } }}
              exit={{ opacity: 0, scale: 0.96, transition: { duration: 0.2 } }}
              whileHover={{ y: -4 }}
            >
              <Link href={`/systems#${s.id}`} className={styles.link}>
                <span className={styles.company}>{s.company}</span>
                <h3>{s.name}</h3>
                <p className={styles.strength}>{s.strength}</p>
                {s.why && <p className={styles.why}>{s.why}</p>}
                <span className={styles.more}>
                  Details <ArrowUpRight size={14} />
                </span>
              </Link>
            </motion.article>
          ))}
        </AnimatePresence>
      </motion.div>
    </section>
  )
}
