import Link from 'next/link'
import { fmtDate, getStats } from '@/lib/api/public'
import { optional } from '@/lib/api/server'
import { PRIMARY_NAV, RESOURCES_NAV } from '../navigation/nav'
import { Wordmark } from '../navigation/Wordmark'
import { MotionToggle } from './MotionToggle'

const CATEGORIES = [
  { href: '/guidelines?category=C07', label: 'Accessibility' },
  { href: '/guidelines?category=C03', label: 'Design tokens' },
  { href: '/guidelines?category=C09', label: 'Engineering & tooling' },
  { href: '/guidelines?category=C08', label: 'Documentation & governance' },
  { href: '/guidelines?category=C10', label: 'Theming' },
]

export async function SiteFooter() {
  const stats = await optional(getStats())
  const checked = fmtDate(stats?.last_sync_at)
  const changed = fmtDate(stats?.content_updated_at)
  return (
    <footer className="mt-32 border-t border-line">
      <div className="container-page grid gap-12 py-16 md:grid-cols-[1.4fr_1fr_1fr_1fr]">
        <div className="flex flex-col gap-5">
          <Wordmark />
          <p className="max-w-sm text-meta text-muted">
            A research index of design systems — every record is collected from public directories and each system&apos;s own documentation,
            and keeps its source.
          </p>
          <Link href="/search" className="focus-ring w-fit text-meta text-accent-text underline decoration-accent/40 underline-offset-4 hover:decoration-accent">Search everything →</Link>
        </div>
        <FooterCol title="Explore" links={PRIMARY_NAV} />
        <FooterCol title="Resources" links={RESOURCES_NAV} />
        <FooterCol title="Topics" links={CATEGORIES} />
      </div>
      <section aria-labelledby="about-directory" className="container-page border-t border-line py-8">
        <h2 id="about-directory" className="eyebrow mb-3">About this directory</h2>
        <p className="max-w-4xl text-[0.82rem] leading-relaxed text-muted">
          This is an independent design-systems discovery and research platform. It is not affiliated with, sponsored by, or endorsed by the
          organizations or projects featured unless explicitly stated. Product names, logos, trademarks, screenshots, and design assets belong to
          their respective owners. Information and links are compiled from publicly available resources for discovery and research purposes.
          Please consult the relevant official documentation for authoritative guidance.
        </p>
        <ul className="mt-4 flex flex-wrap gap-x-6 gap-y-2 text-[0.82rem]">
          <li><Link href="/about" className="focus-ring text-text-2 underline decoration-line-strong underline-offset-4 hover:text-text">Official-source methodology</Link></li>
          <li><Link href="/attribution" className="focus-ring text-text-2 underline decoration-line-strong underline-offset-4 hover:text-text">Attribution &amp; intellectual property</Link></li>
          <li><Link href="/privacy" className="focus-ring text-text-2 underline decoration-line-strong underline-offset-4 hover:text-text">Privacy</Link></li>
        </ul>
      </section>
      <div className="container-page flex flex-col gap-4 border-t border-line py-6 sm:flex-row sm:items-center sm:justify-between">
        <p className="font-mono text-[0.7rem] text-muted">
          {changed ? <>Content updated {changed}</> : checked ? <>Updated {checked}</> : null}
        </p>
        <MotionToggle />
      </div>
    </footer>
  )
}

function FooterCol({ title, links }: { title: string; links: { href: string; label: string }[] }) {
  return (
    <nav aria-label={title}>
      <p className="eyebrow mb-4">{title}</p>
      <ul className="flex flex-col gap-2.5">
        {links.map((l) => (
          <li key={l.href}><Link href={l.href} className="focus-ring text-[0.92rem] text-text-2 transition-colors hover:text-text">{l.label}</Link></li>
        ))}
      </ul>
    </nav>
  )
}
