import Link from 'next/link'
import { ArrowLeft, CloudOff, RotateCcw, SearchX } from 'lucide-react'
import { cn } from '@/lib/cn'
import { buttonVariants } from './button'

/** Public recovery action: always the public homepage, never the admin area. */
export function BackToSite({ className }: { className?: string }) {
  return (
    <Link href="/" className={cn(buttonVariants({ variant: 'secondary', size: 'sm' }), className)}>
      <ArrowLeft className="size-3.5" aria-hidden />Back to Site
    </Link>
  )
}

/** A page-specific recovery link styled like the Back to Site action (e.g. "Clear filters", "Browse design systems"). */
export function RecoveryLink({ href, children }: { href: string; children: React.ReactNode }) {
  return <Link href={href} className={buttonVariants({ variant: 'ghost', size: 'sm' })}>{children}</Link>
}

/**
 * Empty result. Shows the page's own recovery action (if any) followed by "Back to Site". `backToSite={false}` only for
 * small inline sections inside an otherwise working page, where leaving the site would be the wrong suggestion.
 */
export function EmptyState({ title, children, action, className, backToSite = true }: {
  title: string; children?: React.ReactNode; action?: React.ReactNode; className?: string; backToSite?: boolean
}) {
  return (
    <div className={cn('flex flex-col items-start gap-3 border border-dashed border-line-strong px-6 py-10 sm:px-10', className)} role="status">
      <SearchX className="size-6 text-muted" aria-hidden />
      <p className="text-card font-medium">{title}</p>
      {children && <div className="measure text-muted">{children}</div>}
      {(action || backToSite) && <div className="mt-2 flex flex-wrap items-center gap-2">{action}{backToSite && <BackToSite />}</div>}
    </div>
  )
}

/** A failed request is said plainly — never replaced with placeholder content — with "Try again" and "Back to Site". */
export function ErrorNotice({ title = 'This section could not be loaded', message, retryHref, onRetry, className, backToSite = true }: {
  title?: string; message?: string; retryHref?: string; onRetry?: () => void; className?: string; backToSite?: boolean
}) {
  return (
    <div className={cn('flex flex-col items-start gap-2 border border-danger/30 bg-danger/5 px-6 py-6', className)} role="alert">
      <CloudOff className="size-5 text-danger" aria-hidden />
      <p className="font-medium">{title}</p>
      <p className="text-meta text-muted">{message ?? 'The directory service did not respond. Nothing shown here is stale or invented — try again in a moment.'}</p>
      <div className="mt-2 flex flex-wrap items-center gap-2">
        {retryHref && <Link href={retryHref} className={buttonVariants({ variant: 'primary', size: 'sm' })}><RotateCcw className="size-3.5" aria-hidden />Try again</Link>}
        {!retryHref && onRetry && <button type="button" onClick={onRetry} className={buttonVariants({ variant: 'primary', size: 'sm' })}><RotateCcw className="size-3.5" aria-hidden />Try again</button>}
        {backToSite && <BackToSite />}
      </div>
    </div>
  )
}

export function NotDocumented({ children = 'Not documented' }: { children?: React.ReactNode }) {
  return <span className="text-meta text-faint italic">{children}</span>
}
