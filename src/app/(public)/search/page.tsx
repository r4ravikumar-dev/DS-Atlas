import type { Metadata } from 'next'
import Link from 'next/link'
import { ArrowUpRight, Search } from 'lucide-react'
import { getPage } from '@/lib/api/server'
import type { SearchHit } from '@/lib/api/types'
import { hrefWith, type RawParams } from '@/lib/validation/params'
import { cn } from '@/lib/cn'
import { Badge } from '@/components/kit/badge'
import { Button } from '@/components/kit/button'
import { EmptyState, ErrorNotice, RecoveryLink } from '@/components/kit/states'
import { Pagination } from '@/components/kit/pagination'
import { Stagger, StaggerItem } from '@/components/motion/Reveal'

export const metadata: Metadata = { title: 'Search', robots: { index: false, follow: true } }

const TYPES = [
  { value: '', label: 'All' }, { value: 'system', label: 'Systems' }, { value: 'component', label: 'Components' }, { value: 'token', label: 'Tokens' },
  { value: 'guideline', label: 'Guidelines' }, { value: 'pattern', label: 'Patterns' },
]
const LABEL: Record<string, string> = { system: 'Design system', component: 'Component', token: 'Token', guideline: 'Guideline', pattern: 'Pattern', specification: 'Specification', resource: 'Resource' }
const PAGE_SIZE = 20

export default async function SearchPage({ searchParams }: { searchParams: Promise<RawParams> }) {
  const raw = await searchParams
  const q = (Array.isArray(raw.q) ? raw.q[0] : raw.q)?.trim().slice(0, 200) ?? ''
  const type = TYPES.some((t) => t.value === raw.type) ? (raw.type as string) : ''
  const page = Math.max(1, Math.min(500, Number(raw.page) || 1))
  const res = q ? await getPage<SearchHit>('/search', { query: { q, type: type || undefined, page, page_size: PAGE_SIZE }, revalidate: 60, tags: ['search'] }).catch((e: Error) => e) : null
  const facets = (res && !(res instanceof Error) ? res.meta.facets ?? {} : {}) as Record<string, number | string>
  const count = (t: string) => (t === 'guideline' ? Number(facets.guideline ?? 0) + Number(facets.specification ?? 0) : Number(facets[t] ?? 0))

  return (
    <>
      <header className="border-b border-line">
        <div className="container-page flex flex-col gap-8 pt-14 pb-10 md:pt-20">
          <div>
            <p className="eyebrow mb-4">Search</p>
            <h1 className="text-title font-medium">{q ? <>Results for <span className="font-serif font-normal text-accent-text italic">“{q}”</span></> : 'Search the whole index'}</h1>
          </div>
          <form role="search" action="/search" className="relative max-w-2xl">
            <label htmlFor="search-q" className="sr-only">Search design systems, components, tokens and guidelines</label>
            <Search className="pointer-events-none absolute top-1/2 left-4 size-5 -translate-y-1/2 text-muted" aria-hidden />
            <input id="search-q" name="q" type="search" defaultValue={q} maxLength={200} placeholder="e.g. dialog, semantic tokens, keyboard, governance…"
              className="focus-ring h-14 w-full rounded-md border border-line-strong bg-surface pr-32 pl-12 text-base placeholder:text-faint focus:border-accent focus:outline-none" />
            {type && <input type="hidden" name="type" value={type} />}
            <Button type="submit" variant="primary" className="absolute top-2 right-2 h-10">Search</Button>
          </form>
          {q && res && !(res instanceof Error) && (
            <nav aria-label="Result types" className="flex flex-wrap gap-1.5">
              {TYPES.map((t) => {
                const n = t.value ? count(t.value) : undefined
                if (t.value && !n) return null
                return (
                  <Link key={t.value} href={hrefWith('/search', { q }, { type: t.value || null })} aria-current={type === t.value ? 'page' : undefined}
                    className={cn('focus-ring inline-flex h-8 items-center gap-2 rounded-xs border px-3 text-meta transition-colors', type === t.value ? 'border-transparent bg-text text-bg' : 'border-line-strong text-text-2 hover:border-text/40')}>
                    {t.label}{n ? <span className="font-mono text-[0.68rem] opacity-70">{n.toLocaleString()}</span> : null}
                  </Link>
                )
              })}
            </nav>
          )}
        </div>
      </header>
      <div className="container-page pt-10">
        {!q ? <EmptyState title="Type a term to search systems, components, tokens and guidance">Matching uses full-text search with prefixes, across titles, organisations and summaries.</EmptyState>
          : res instanceof Error ? <ErrorNotice title="Search is unavailable right now" message={res.message} retryHref={hrefWith('/search', raw, {})} />
          : !res || res.data.length === 0 ? <EmptyState title={`No results for “${q}”`} action={<RecoveryLink href="/search">Clear search</RecoveryLink>}>Try fewer or broader terms.</EmptyState>
          : (
            <>
              {facets._match_mode === 'any' && <p className="mb-6 text-meta text-muted">No record contains every term — showing records that match any of them, ranked by relevance.</p>}
              <p className="mb-4 font-mono text-meta text-muted" aria-live="polite">{res.meta.total_items.toLocaleString()} results</p>
              <Stagger as="ul" key={`${q}-${type}-${page}`} gap={0.03} className="divide-y divide-line border-y border-line">
                {res.data.map((h) => {
                  const publicUrl = h.url && !h.url.startsWith('/admin') ? h.url : null
                  const body = (
                    <>
                      <span className="flex flex-wrap items-center gap-2">
                        <Badge tone="muted">{LABEL[h.type] ?? h.type}</Badge>
                        <span className="text-card font-medium text-text group-hover:text-accent-text">{h.title}</span>
                        {h.subtitle && <span className="text-meta text-muted">· {h.subtitle}</span>}
                        {publicUrl && <ArrowUpRight className="ml-auto size-4 text-faint transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" aria-hidden />}
                      </span>
                      {/* ts_headline marks matches with <b>: split into text + <mark>, never rendered as HTML */}
                      {h.snippet && <span className="measure mt-1.5 block text-[0.9rem] text-text-2">{h.snippet.split(/<\/?b>/).map((part, i) => (i % 2 ? <mark key={i} className="rounded-[2px] bg-accent-soft px-0.5 text-text">{part}</mark> : part))}</span>}
                    </>
                  )
                  return (
                    <StaggerItem as="li" key={`${h.type}-${h.id}`}>
                      {publicUrl ? <Link href={publicUrl} className="focus-ring group block py-5">{body}</Link> : <div className="py-5">{body}</div>}
                    </StaggerItem>
                  )
                })}
              </Stagger>
              <Pagination page={page} totalPages={res.meta.total_pages} total={res.meta.total_items} pageSize={PAGE_SIZE} href={(n) => hrefWith('/search', raw, { page: n })} />
            </>
          )}
      </div>
    </>
  )
}
