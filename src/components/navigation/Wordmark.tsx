import { cn } from '@/lib/cn'

/** Product mark: four tiles (system, component, token, document) with a typographic wordmark. */
export function Wordmark({ className, compact }: { className?: string; compact?: boolean }) {
  return (
    <span className={cn('inline-flex items-center gap-2.5', className)}>
      <span aria-hidden className="grid size-6 grid-cols-2 gap-[3px]">
        <i className="rounded-[2px] bg-accent" />
        <i className="rounded-[2px] bg-text/80" />
        <i className="rounded-[2px] bg-text/30" />
        <i className="rounded-full bg-text/80" />
      </span>
      {!compact && (
        <span className="truncate text-[0.95rem] leading-none font-medium tracking-tight">
          Design Systems <span className="font-serif text-[1.05rem] text-muted italic max-[360px]:hidden">Directory</span>
        </span>
      )}
    </span>
  )
}
