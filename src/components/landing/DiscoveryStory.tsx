'use client'

import { useRef } from 'react'
import Link from 'next/link'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { useGSAP } from '@gsap/react'
import { ArrowRight } from 'lucide-react'
import { useMotionPreference } from '@/lib/motion/useMotionAllowed'

gsap.registerPlugin(useGSAP, ScrollTrigger)

export interface StoryNode {
  /** e.g. "Design system" */
  role: string
  /** real record label, e.g. "Carbon" — or null when the example record is missing */
  label: string | null
  href: string
}

const STEPS = [
  { title: 'Compare implementation approaches', body: 'Put two to six systems side by side — frameworks, styling, tokens, accessibility and documentation — with every cell traced to evidence.', href: '/compare', cta: 'Open the comparison workspace' },
  { title: 'Explore individual components', body: 'Each library’s Button stays its own Button: props, types, defaults, variants and keyboard behaviour as documented by that library.', href: '/components', cta: 'Browse components' },
  { title: 'Inspect token relationships', body: 'See the original token, its alias chain and the resolved value where the source states one — never an invented scale.', href: '/tokens', cta: 'Open the token explorer' },
  { title: 'Find official documentation', body: 'Website, docs, GitHub, Figma and Storybook links, gathered from the system’s own pages and public directories.', href: '/systems?resource=official_documentation', cta: 'Systems with documentation' },
  { title: 'Discover source repositories', body: 'Jump from any system to its GitHub repository and the Storybook it publishes, then into individual stories.', href: '/systems?resource=github_repository', cta: 'Systems with repositories' },
]

/**
 * Scroll-told explanation of how the index connects. On wide screens the diagram stays pinned (CSS sticky — no
 * scroll hijacking) while each step scrubs in the next connection. Reduced motion: the full diagram, no scrubbing.
 */
export function DiscoveryStory({ nodes }: { nodes: StoryNode[] }) {
  const scope = useRef<HTMLElement>(null)
  const pref = useMotionPreference()

  useGSAP(
    () => {
      if (pref !== 'allowed') return
      const mm = gsap.matchMedia()
      mm.add('(min-width: 1024px)', () => {
        const edges = gsap.utils.toArray<SVGPathElement>('[data-edge]')
        const dots = gsap.utils.toArray<SVGGElement>('[data-node]')
        edges.forEach((e) => {
          const len = e.getTotalLength()
          gsap.set(e, { strokeDasharray: len, strokeDashoffset: len })
        })
        gsap.set(dots.slice(1), { opacity: 0.25 })
        gsap.utils.toArray<HTMLElement>('[data-step]').forEach((step, i) => {
          const tl = gsap.timeline({ scrollTrigger: { trigger: step, start: 'top 70%', end: 'top 35%', scrub: 0.6 } })
          if (i > 0 && edges[i - 1]) tl.to(edges[i - 1], { strokeDashoffset: 0, ease: 'none' }, 0)
          if (i > 0 && dots[i]) tl.to(dots[i], { opacity: 1, ease: 'none' }, 0.2)
          gsap.fromTo(step, { opacity: 0.35 }, { opacity: 1, scrollTrigger: { trigger: step, start: 'top 75%', end: 'top 45%', scrub: true } })
        })
      })
      return () => mm.revert()
    },
    { scope, dependencies: [pref] },
  )

  // node positions along a gentle diagonal (viewBox 0 0 400 520)
  const P = [[70, 60], [250, 150], [110, 260], [290, 360], [140, 465]] as const
  const path = (a: readonly number[], b: readonly number[]) => `M${a[0]},${a[1]} C${a[0] + 120},${a[1] + 10} ${b[0] - 120},${b[1] - 10} ${b[0]},${b[1]}`

  return (
    <section ref={scope} aria-labelledby="story-title" className="container-page py-28">
      <div className="mb-16 max-w-3xl">
        <p className="eyebrow mb-4">03 — How the index connects</p>
        <h2 id="story-title" className="text-title font-medium">From a system to the line of documentation <span className="font-serif font-normal text-muted italic">that proves it.</span></h2>
      </div>
      <div className="grid gap-12 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
        <div className="lg:sticky lg:top-[calc(var(--header-h)+3rem)] lg:h-[520px]" aria-hidden>
          <svg viewBox="0 0 400 520" className="h-auto w-full max-w-md">
            {P.slice(0, -1).map((a, i) => (
              <path key={i} data-edge d={path(a, P[i + 1])} fill="none" stroke="var(--accent)" strokeWidth="1.25" strokeOpacity="0.8" />
            ))}
            {P.map(([x, y], i) => (
              <g key={i} data-node transform={`translate(${x} ${y})`}>
                <circle r={i === 0 ? 9 : 6} fill={i === 0 ? 'var(--accent)' : 'var(--bg)'} stroke={i === 0 ? 'none' : 'var(--text)'} strokeWidth="1.25" />
                <text x="18" y="-4" fill="var(--muted)" fontSize="10" fontFamily="var(--font-mono)" letterSpacing="0.08em">{nodes[i]?.role.toUpperCase()}</text>
                <text x="18" y="13" fill="var(--text)" fontSize="15">{nodes[i]?.label ?? '—'}</text>
              </g>
            ))}
          </svg>
          <p className="mt-2 font-mono text-[0.68rem] text-faint">A real path through the index — the records named here exist and are linked below.</p>
        </div>
        <ol className="flex flex-col">
          {STEPS.map((s, i) => (
            <li key={s.title} data-step className="border-t border-line py-10 first:border-t-0 first:pt-0 lg:min-h-[44vh]">
              <p className="mb-3 font-mono text-meta text-accent-text">{String(i + 1).padStart(2, '0')}</p>
              <h3 className="mb-3 text-section font-medium">{s.title}</h3>
              <p className="measure mb-5 text-text-2">{s.body}</p>
              <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-meta">
                <Link href={s.href} className="focus-ring inline-flex items-center gap-1.5 text-text underline-offset-4 hover:underline">{s.cta} <ArrowRight className="size-3.5" aria-hidden /></Link>
                {nodes[i]?.label && <Link href={nodes[i].href} className="focus-ring text-muted underline-offset-4 hover:text-text hover:underline">Example: {nodes[i].label}</Link>}
              </div>
            </li>
          ))}
        </ol>
      </div>
    </section>
  )
}
