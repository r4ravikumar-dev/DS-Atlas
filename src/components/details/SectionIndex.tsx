'use client'

import { useEffect, useState } from 'react'
import { motion } from 'motion/react'
import { spring } from '@/lib/motion/tokens'
import { cn } from '@/lib/cn'

/**
 * Sticky in-page index for long research pages. Highlights the section in view (scroll-spy via IntersectionObserver);
 * on small screens it becomes a horizontally scrollable strip. Plain anchor links, so it works without JS.
 */
export function SectionIndex({ sections }: { sections: { id: string; label: string; count?: number }[] }) {
  const [active, setActive] = useState(sections[0]?.id)
  useEffect(() => {
    const els = sections.map((s) => document.getElementById(s.id)).filter(Boolean) as HTMLElement[]
    const io = new IntersectionObserver(
      (entries) => {
        const top = entries.filter((e) => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0]
        if (top) setActive(top.target.id)
      },
      { rootMargin: '-20% 0px -65% 0px' },
    )
    els.forEach((el) => io.observe(el))
    return () => io.disconnect()
  }, [sections])

  return (
    <nav aria-label="On this page" className="sticky top-(--header-h) z-20 -mx-(--gutter) border-b border-line bg-glass px-(--gutter) backdrop-blur-xl lg:top-[calc(var(--header-h)+2rem)] lg:mx-0 lg:border-0 lg:bg-transparent lg:px-0 lg:backdrop-blur-none">
      <p className="eyebrow mb-3 hidden lg:block">On this page</p>
      <ul className="flex gap-1 overflow-x-auto py-2 [scrollbar-width:none] lg:flex-col lg:gap-0.5 lg:overflow-visible lg:py-0">
        {sections.map((s) => (
          <li key={s.id} className="shrink-0">
            <a href={`#${s.id}`} aria-current={active === s.id ? 'true' : undefined}
              className={cn('focus-ring relative flex items-center justify-between gap-3 rounded-xs px-3 py-1.5 text-[0.88rem] transition-colors lg:pl-4', active === s.id ? 'text-text' : 'text-muted hover:text-text')}>
              {active === s.id && <motion.span layoutId="section-index" transition={spring.snappy} className="absolute inset-0 rounded-xs bg-surface-2 lg:inset-y-1 lg:right-auto lg:left-0 lg:w-0.5 lg:rounded-none lg:bg-accent" />}
              <span className="relative">{s.label}</span>
              {s.count !== undefined && <span className="relative font-mono text-[0.68rem] text-faint tabular-nums">{s.count.toLocaleString()}</span>}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  )
}
