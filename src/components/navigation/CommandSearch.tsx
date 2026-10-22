'use client'

import { useEffect, useId, useMemo, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Dialog } from 'radix-ui'
import { AnimatePresence, motion } from 'motion/react'
import { ArrowRight, Boxes, CornerDownLeft, FileText, Layers, Loader2, Palette, Search } from 'lucide-react'
import { useSearch } from '@/features/search/api'
import { useDebounced } from '@/hooks/useDebounced'
import { duration, ease, spring } from '@/lib/motion/tokens'
import type { SearchHit } from '@/lib/api/types'
import { cn } from '@/lib/cn'

const TYPE_LABEL: Record<string, string> = { system: 'Design system', component: 'Component', token: 'Token', guideline: 'Guideline', pattern: 'Pattern', specification: 'Specification', resource: 'Resource' }
const TYPE_ICON: Record<string, typeof Boxes> = { system: Layers, component: Boxes, token: Palette }

const QUICK = [
  { href: '/systems', label: 'Browse all design systems', icon: Layers },
  { href: '/components', label: 'Explore components across systems', icon: Boxes },
  { href: '/tokens', label: 'Inspect design tokens', icon: Palette },
  { href: '/guidelines', label: 'Read guidelines and checklists', icon: FileText },
]

/** Only public destinations are offered (search can also index records that live in the admin area). */
const publicHit = (h: SearchHit) => !!h.url && !h.url.startsWith('/admin')

/** Search dialog (⌘K / Ctrl K, or "/"): live results from the backend search index, keyboard navigable listbox. */
export function CommandSearch({ open, onOpenChange }: { open: boolean; onOpenChange: (o: boolean) => void }) {
  const router = useRouter()
  const [q, setQ] = useState('')
  const dq = useDebounced(q.trim(), 180)
  const res = useSearch({ q: dq, page_size: 10 })
  const hits = useMemo(() => (dq ? (res.data?.data ?? []).filter(publicHit) : []), [dq, res.data])
  const items = dq ? [...hits.map((h) => ({ href: h.url!, key: `${h.type}-${h.id}` })), { href: `/search?q=${encodeURIComponent(dq)}`, key: 'all' }] : QUICK.map((x) => ({ href: x.href, key: x.href }))
  const [active, setActive] = useState(0)
  const listId = useId()
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => setActive(0), [dq, open])

  const go = (href: string) => {
    onOpenChange(false)
    router.push(href)
  }
  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') (e.preventDefault(), setActive((a) => Math.min(items.length - 1, a + 1)))
    else if (e.key === 'ArrowUp') (e.preventDefault(), setActive((a) => Math.max(0, a - 1)))
    else if (e.key === 'Enter' && items[active]) (e.preventDefault(), go(items[active].href))
  }
  const optId = (i: number) => `${listId}-opt-${i}`

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <AnimatePresence>
        {open && (
          <Dialog.Portal forceMount>
            <Dialog.Overlay asChild forceMount>
              <motion.div className="fixed inset-0 z-50 bg-overlay backdrop-blur-sm" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: duration.fast }} />
            </Dialog.Overlay>
            <Dialog.Content asChild forceMount onOpenAutoFocus={(e) => (e.preventDefault(), inputRef.current?.focus())}>
              <motion.div
                className="fixed inset-x-3 top-[10vh] z-50 mx-auto max-w-2xl overflow-hidden rounded-md border border-line-strong bg-bg shadow-2 outline-none"
                initial={{ opacity: 0, y: -12, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: -8, scale: 0.98 }} transition={spring.gentle}
              >
                <Dialog.Title className="sr-only">Search the directory</Dialog.Title>
                <Dialog.Description className="sr-only">Type to search design systems, components, tokens and guidelines. Use the arrow keys to move through results.</Dialog.Description>
                <div className="flex items-center gap-3 border-b border-line px-4">
                  {res.isFetching ? <Loader2 className="size-4 animate-spin text-muted" aria-hidden /> : <Search className="size-4 text-muted" aria-hidden />}
                  <input
                    ref={inputRef} value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={onKey} maxLength={200}
                    placeholder="Search systems, components, tokens…" aria-label="Search" role="combobox" aria-expanded aria-controls={listId}
                    aria-activedescendant={items.length ? optId(active) : undefined} aria-autocomplete="list"
                    className="h-14 w-full bg-transparent text-base text-text outline-none placeholder:text-faint"
                  />
                  <kbd className="hidden rounded-xs border border-line px-1.5 py-0.5 font-mono text-[0.65rem] text-muted sm:block">esc</kbd>
                </div>
                <ul id={listId} role="listbox" aria-label={dq ? 'Search results' : 'Suggestions'} className="max-h-[60vh] overflow-y-auto p-2">
                  {!dq && QUICK.map((x, i) => (
                    <Option key={x.href} id={optId(i)} active={i === active} onHover={() => setActive(i)} onPick={() => go(x.href)}>
                      <x.icon className="size-4 text-muted" aria-hidden /><span>{x.label}</span>
                    </Option>
                  ))}
                  {dq && res.isError && <li className="px-3 py-6 text-meta text-danger" role="alert">Search is unavailable right now.</li>}
                  {dq && !res.isFetching && res.data && hits.length === 0 && <li className="px-3 py-6 text-meta text-muted">No results for “{dq}”.</li>}
                  {hits.map((h, i) => {
                    const Icon = TYPE_ICON[h.type] ?? FileText
                    return (
                      <Option key={`${h.type}-${h.id}`} id={optId(i)} active={i === active} onHover={() => setActive(i)} onPick={() => go(h.url!)}>
                        <Icon className="size-4 shrink-0 text-muted" aria-hidden />
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-text">{h.title}</span>
                          {h.subtitle && <span className="block truncate text-meta text-muted">{h.subtitle}</span>}
                        </span>
                        <span className="eyebrow shrink-0">{TYPE_LABEL[h.type] ?? h.type}</span>
                      </Option>
                    )
                  })}
                  {dq && (
                    <Option id={optId(hits.length)} active={active === hits.length} onHover={() => setActive(hits.length)} onPick={() => go(`/search?q=${encodeURIComponent(dq)}`)}>
                      <ArrowRight className="size-4 text-accent-text" aria-hidden />
                      <span>See all results{res.data ? ` (${res.data.meta.total_items.toLocaleString()})` : ''}</span>
                    </Option>
                  )}
                </ul>
                <div className="flex items-center gap-4 border-t border-line px-4 py-2 font-mono text-[0.65rem] text-muted">
                  <span className="inline-flex items-center gap-1"><CornerDownLeft className="size-3" aria-hidden /> open</span>
                  <span>↑ ↓ move</span>
                </div>
              </motion.div>
            </Dialog.Content>
          </Dialog.Portal>
        )}
      </AnimatePresence>
    </Dialog.Root>
  )
}

function Option({ id, active, onHover, onPick, children }: { id: string; active: boolean; onHover: () => void; onPick: () => void; children: React.ReactNode }) {
  return (
    <li id={id} role="option" aria-selected={active} onMouseMove={onHover} onClick={onPick}
      className={cn('relative flex cursor-pointer items-center gap-3 rounded-sm px-3 py-2.5 text-[0.92rem]', active ? 'text-text' : 'text-text-2')}>
      {active && <motion.span layoutId="cmd-active" className="absolute inset-0 -z-10 rounded-sm bg-surface-2" transition={{ duration: duration.fast, ease: ease.out }} />}
      {children}
    </li>
  )
}
