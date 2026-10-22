import Link from 'next/link'
import { ArrowLeft, ArrowRight } from 'lucide-react'
import { cn } from '@/lib/cn'

/** Link-based pagination — works without JavaScript and keeps every page crawlable. */
export function Pagination({ page, totalPages, total, pageSize, href }: { page: number; totalPages: number; total: number; pageSize: number; href: (page: number) => string }) {
  if (totalPages <= 1) return null
  const from = (page - 1) * pageSize + 1
  const to = Math.min(total, page * pageSize)
  const pages = window5(page, totalPages)
  const cell = 'focus-ring inline-flex h-9 min-w-9 items-center justify-center rounded-sm px-2 font-mono text-meta transition-colors'
  return (
    <nav aria-label="Pagination" className="mt-10 flex flex-wrap items-center justify-between gap-4 border-t border-line pt-6">
      <p className="font-mono text-meta text-muted">{from.toLocaleString()}–{to.toLocaleString()} of {total.toLocaleString()}</p>
      <ul className="flex items-center gap-1">
        <li>{page > 1 ? <Link className={cn(cell, 'hover:bg-surface-2')} href={href(page - 1)} rel="prev" aria-label="Previous page"><ArrowLeft className="size-4" /></Link> : <span className={cn(cell, 'opacity-30')} aria-hidden><ArrowLeft className="size-4" /></span>}</li>
        {pages.map((p, i) => (
          <li key={i}>
            {p === null ? <span className={cn(cell, 'text-faint')}>…</span>
              : <Link className={cn(cell, p === page ? 'bg-text text-bg' : 'text-text-2 hover:bg-surface-2')} href={href(p)} aria-current={p === page ? 'page' : undefined}>{p}</Link>}
          </li>
        ))}
        <li>{page < totalPages ? <Link className={cn(cell, 'hover:bg-surface-2')} href={href(page + 1)} rel="next" aria-label="Next page"><ArrowRight className="size-4" /></Link> : <span className={cn(cell, 'opacity-30')} aria-hidden><ArrowRight className="size-4" /></span>}</li>
      </ul>
    </nav>
  )
}

function window5(page: number, total: number): (number | null)[] {
  const set = new Set([1, total, page - 1, page, page + 1].filter((p) => p >= 1 && p <= total))
  const sorted = [...set].sort((a, b) => a - b)
  const out: (number | null)[] = []
  sorted.forEach((p, i) => {
    if (i && p - sorted[i - 1] > 1) out.push(null)
    out.push(p)
  })
  return out
}
