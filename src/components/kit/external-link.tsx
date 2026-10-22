import { ArrowUpRight } from 'lucide-react'
import { cn } from '@/lib/cn'

export function prettyUrl(u: string) {
  try {
    const x = new URL(u)
    return (x.host.replace(/^www\./, '') + x.pathname).replace(/\/$/, '')
  } catch {
    return u
  }
}

/** Outbound link to an official resource. Only http(s) URLs are rendered as links. */
export function ExternalLink({ href, children, className }: { href: string; children?: React.ReactNode; className?: string }) {
  if (!/^https?:\/\//i.test(href)) return <span className={className}>{children ?? href}</span>
  return (
    <a href={href} target="_blank" rel="noopener noreferrer nofollow" className={cn('focus-ring group/link inline-flex items-center gap-1 underline-offset-4 hover:underline', className)}>
      {children ?? prettyUrl(href)}
      <ArrowUpRight className="size-3.5 shrink-0 opacity-60 transition-transform duration-200 group-hover/link:translate-x-0.5 group-hover/link:-translate-y-0.5" aria-hidden />
      <span className="sr-only">(opens in a new tab)</span>
    </a>
  )
}
