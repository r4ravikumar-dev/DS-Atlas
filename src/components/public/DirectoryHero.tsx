'use client'

import Link from 'next/link'
import { useStats } from '@/features/public/api'
import { Skeleton } from '../ui'
import s from './DirectoryHero.module.scss'

/** Headline counts of the published dataset, computed by the backend. */
export function DirectoryHero() {
  const { data, error } = useStats()
  const n = (v?: number) => (v === undefined ? <Skeleton w={48} h={22} /> : v.toLocaleString())
  return (
    <section className={s.hero} aria-labelledby="hero-title">
      <h1 id="hero-title">Explore design systems, component by component.</h1>
      <p>
        Components, variants, design tokens, guidelines and Storybook stories collected from public directories and each system&apos;s
        own documentation — with the official website, docs, GitHub and Figma links, and the evidence behind every record.
      </p>
      {!error && (
        <dl className={s.stats}>
          <div><dt>Design systems</dt><dd>{n(data?.design_systems)}</dd></div>
          <div><dt><Link href="/components">Components</Link></dt><dd>{n(data?.components)}</dd></div>
          <div><dt><Link href="/storybook?tab=variants">Variants</Link></dt><dd>{n(data?.variants)}</dd></div>
          <div><dt><Link href="/storybook?tab=stories">Stories</Link></dt><dd>{n(data?.stories)}</dd></div>
          <div><dt><Link href="/tokens">Tokens</Link></dt><dd>{n(data?.tokens)}</dd></div>
          <div><dt><Link href="/guidelines">Guidelines</Link></dt><dd>{n(data && data.guidelines + data.patterns)}</dd></div>
        </dl>
      )}
    </section>
  )
}
