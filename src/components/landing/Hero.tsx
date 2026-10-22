import Link from 'next/link'
import { ArrowRight, Search } from 'lucide-react'
import { Button } from '../kit/button'
import { HeroIllustration } from './HeroIllustration'

/**
 * Landing hero: headline, one-line value statement, search and two ways in, next to an illustration of what the index
 * catalogues. Server-rendered; the search is a plain GET form, so it works before (and without) JavaScript.
 */
export function Hero({ systems }: { systems: number | null }) {
  return (
    <section aria-labelledby="hero-title" className="border-b border-line">
      <div className="container-page grid items-center gap-12 py-16 md:py-24 lg:grid-cols-[1.1fr_1fr] lg:gap-16">
        <div className="flex flex-col gap-7">
          {systems && <p className="eyebrow">{systems.toLocaleString()} design systems indexed</p>}
          <h1 id="hero-title" className="text-[clamp(2.4rem,1.6rem+3.6vw,4.5rem)] leading-[1] font-medium tracking-[-0.04em]">
            Explore design systems,{' '}
            <span className="font-serif font-normal text-accent-text italic">component by component.</span>
          </h1>
          <p className="max-w-[44ch] text-lg text-text-2">
            Components, tokens, patterns and official resources from hundreds of design systems — in one searchable place.
          </p>
          <form role="search" action="/search" className="relative max-w-lg">
            <label htmlFor="hero-search" className="sr-only">Search design systems, components, tokens and patterns</label>
            <Search className="pointer-events-none absolute top-1/2 left-4 size-4.5 -translate-y-1/2 text-muted" aria-hidden />
            <input id="hero-search" name="q" type="search" required maxLength={200} autoComplete="off" placeholder="Search “date picker”, “Carbon”, “color.primary”"
              className="focus-ring h-13 w-full rounded-md border border-line-strong bg-surface pr-28 pl-11 text-[0.95rem] text-text placeholder:text-faint hover:border-text/30 focus:border-accent focus:outline-none" />
            <Button type="submit" variant="primary" size="sm" className="absolute top-1/2 right-2 h-9 -translate-y-1/2">Search</Button>
          </form>
          <div className="flex flex-wrap items-center gap-2">
            <Button asChild variant="secondary"><Link href="/systems">Browse design systems <ArrowRight className="size-4" aria-hidden /></Link></Button>
            <Button asChild variant="ghost"><Link href="/playground">Try components live</Link></Button>
          </div>
        </div>
        <div className="hidden md:block">
          <HeroIllustration />
        </div>
      </div>
    </section>
  )
}
