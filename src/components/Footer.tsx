import Link from 'next/link'
import { NAV } from '@/lib/nav'
import styles from './Footer.module.scss'

const SOURCES = [
  { label: 'thedesignsystem.guide', href: 'https://thedesignsystem.guide/resources' },
  { label: 'designsystems.com', href: 'https://www.designsystems.com' },
  { label: 'designsystems.one', href: 'https://www.designsystems.one/design-systems' },
  { label: 'Design System Checklist', href: 'https://github.com/ardakaracizmeli/design-system-checklist' },
  { label: 'awesome-design-systems', href: 'https://github.com/alexpate/awesome-design-systems' },
]

export function Footer() {
  return (
    <footer className={styles.footer}>
      <div className="container">
        <div className={styles.big} aria-hidden>
          Build the <span className="serif">system</span>,
          <br /> not the screens.
        </div>
        <div className={styles.grid}>
          <div>
            <p className="mono">Explore</p>
            <ul>
              {NAV.map((n) => (
                <li key={n.href}>
                  <Link href={n.href}>{n.label}</Link>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <p className="mono">Curated from</p>
            <ul>
              {SOURCES.map((s) => (
                <li key={s.href}>
                  <a href={s.href} target="_blank" rel="noopener noreferrer">
                    {s.label} ↗
                  </a>
                </li>
              ))}
            </ul>
          </div>
          <div className={styles.note}>
            <p className="mono">About</p>
            <p>
              An independent, interactive atlas of public design systems, tooling and practice. All trademarks belong to their owners; links go to
              official sources.
            </p>
            <p className={styles.kbd}>
              Press <kbd>⌘K</kbd> anywhere to search.
            </p>
          </div>
        </div>
      </div>
    </footer>
  )
}
