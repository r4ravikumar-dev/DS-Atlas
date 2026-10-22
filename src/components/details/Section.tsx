import { cn } from '@/lib/cn'

/** A titled section of a research page; `id` is the anchor used by <SectionIndex>. */
export function Section({ id, title, count, action, children, className }: { id: string; title: string; count?: number; action?: React.ReactNode; children: React.ReactNode; className?: string }) {
  return (
    <section id={id} aria-labelledby={`${id}-title`} className={cn('scroll-mt-[calc(var(--header-h)+4rem)] border-t border-line pt-10', className)}>
      <div className="mb-8 flex flex-wrap items-baseline justify-between gap-4">
        <h2 id={`${id}-title`} className="text-section font-medium">
          {title}{count !== undefined && <span className="ml-3 align-middle font-mono text-meta text-muted tabular-nums">{count.toLocaleString()}</span>}
        </h2>
        {action}
      </div>
      {children}
    </section>
  )
}
