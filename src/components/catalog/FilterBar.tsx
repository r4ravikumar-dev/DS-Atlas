'use client'

import { useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { LayoutGrid, List, Loader2, Search, SlidersHorizontal, X } from 'lucide-react'
import { useDebounced } from '@/hooks/useDebounced'
import { duration, spring } from '@/lib/motion/tokens'
import { cn } from '@/lib/cn'
import { Sheet } from '../kit/sheet'
import { useFilters } from './FilterState'

export interface FilterOption { value: string; label?: string; count?: number }
export interface FilterGroup { param: string; label: string; options: FilterOption[]; single?: boolean }
export interface FilterToggle { param: string; label: string; value?: string }

interface Props {
  searchPlaceholder: string
  groups: FilterGroup[]
  toggles?: FilterToggle[]
  sorts?: { value: string; label: string }[]
  view?: boolean
}

/** Search + sort + view controls (top bar) and the facet panel (sidebar on desktop, sheet on mobile). */
export function FilterBar({ searchPlaceholder, groups, toggles = [], sorts, view }: Props) {
  const { params, update, pending } = useFilters()
  const [q, setQ] = useState(params.get('q') ?? '')
  const dq = useDebounced(q, 350)
  const [sheet, setSheet] = useState(false)

  useEffect(() => {
    if ((params.get('q') ?? '') !== dq.trim()) update({ q: dq.trim() || null })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dq])

  const active = [
    ...groups.flatMap((g) => params.getAll(g.param).map((v) => ({ param: g.param, value: v, label: g.options.find((o) => o.value === v)?.label ?? v, group: g.label }))),
    ...toggles.filter((t) => params.has(t.param)).map((t) => ({ param: t.param, value: params.get(t.param)!, label: t.label, group: '' })),
  ]
  const remove = (param: string, value: string) => update({ [param]: params.getAll(param).filter((v) => v !== value) })

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative min-w-0 flex-1 basis-64">
          {pending ? <Loader2 className="absolute top-1/2 left-3.5 size-4 -translate-y-1/2 animate-spin text-muted" aria-hidden /> : <Search className="absolute top-1/2 left-3.5 size-4 -translate-y-1/2 text-muted" aria-hidden />}
          <label htmlFor="filter-q" className="sr-only">{searchPlaceholder}</label>
          <input id="filter-q" type="search" value={q} onChange={(e) => setQ(e.target.value)} maxLength={200} placeholder={searchPlaceholder} autoComplete="off"
            className="focus-ring h-11 w-full rounded-sm border border-line-strong bg-surface pr-3 pl-10 text-[0.95rem] text-text placeholder:text-faint hover:border-text/30 focus:border-accent focus:outline-none" />
        </div>
        {sorts && (
          <label className="flex h-11 items-center gap-2 rounded-sm border border-line-strong bg-surface pr-1 pl-3 text-meta text-muted">
            Sort
            <select value={params.get('sort') ?? ''} onChange={(e) => update({ sort: e.target.value || null })} className="focus-ring h-9 rounded-xs border-0 bg-transparent pr-1 text-text outline-none">
              {sorts.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
            </select>
          </label>
        )}
        {view && <ViewToggle value={params.get('view') === 'list' ? 'list' : 'grid'} onChange={(v) => update({ view: v === 'grid' ? null : v, page: params.get('page') })} />}
        <button type="button" onClick={() => setSheet(true)} className="focus-ring inline-flex h-11 items-center gap-2 rounded-sm border border-line-strong bg-surface px-3 text-meta text-text lg:hidden">
          <SlidersHorizontal className="size-4" aria-hidden /> Filters{active.length ? ` (${active.length})` : ''}
        </button>
      </div>
      <AnimatePresence initial={false}>
        {active.length > 0 && (
          <motion.ul initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} transition={{ duration: duration.fast }}
            className="flex flex-wrap items-center gap-1.5" aria-label="Active filters">
            <AnimatePresence initial={false}>
              {active.map((a) => (
                <motion.li key={a.param + a.value} layout initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.9 }} transition={spring.snappy}>
                  <button type="button" onClick={() => remove(a.param, a.value)} className="focus-ring inline-flex h-7 items-center gap-1.5 rounded-xs border border-line-strong bg-surface-2 px-2 text-meta text-text hover:border-text/40">
                    {a.group && <span className="text-muted">{a.group}:</span>} {a.label} <X className="size-3" aria-hidden /><span className="sr-only">Remove filter</span>
                  </button>
                </motion.li>
              ))}
            </AnimatePresence>
            <li><button type="button" onClick={() => update(Object.fromEntries([...groups.map((g) => [g.param, null]), ...toggles.map((t) => [t.param, null]), ['q', null]]))} className="focus-ring h-7 px-2 text-meta text-muted underline-offset-4 hover:text-text hover:underline">Clear all</button></li>
          </motion.ul>
        )}
      </AnimatePresence>
      <Sheet open={sheet} onOpenChange={setSheet} side="left" title="Filters" description="Results update as you choose.">
        <FacetPanel groups={groups} toggles={toggles} />
      </Sheet>
    </div>
  )
}

function ViewToggle({ value, onChange }: { value: 'grid' | 'list'; onChange: (v: 'grid' | 'list') => void }) {
  return (
    <div role="radiogroup" aria-label="Layout" className="relative hidden h-11 items-center rounded-sm border border-line-strong bg-surface p-1 sm:flex">
      {(['grid', 'list'] as const).map((v) => (
        <button key={v} type="button" role="radio" aria-checked={value === v} onClick={() => onChange(v)} aria-label={v === 'grid' ? 'Grid' : 'List'}
          className={cn('focus-ring relative grid size-9 place-items-center rounded-xs transition-colors', value === v ? 'text-accent-ink' : 'text-muted hover:text-text')}>
          {value === v && <motion.span layoutId="view-toggle" className="absolute inset-0 rounded-xs bg-accent" transition={spring.snappy} />}
          {v === 'grid' ? <LayoutGrid className="relative size-4" /> : <List className="relative size-4" />}
        </button>
      ))}
    </div>
  )
}

/** Facet checkboxes. Only values that exist in the dataset are offered (they come from the backend facet endpoints). */
export function FacetPanel({ groups, toggles = [], className }: { groups: FilterGroup[]; toggles?: FilterToggle[]; className?: string }) {
  const { params, update } = useFilters()
  return (
    <div className={cn('flex flex-col gap-8', className)}>
      {toggles.length > 0 && (
        <fieldset className="flex flex-col gap-2.5">
          <legend className="eyebrow mb-3">Availability</legend>
          {toggles.map((t) => (
            <Check key={t.param} label={t.label} checked={params.has(t.param)} onChange={(on) => update({ [t.param]: on ? (t.value ?? 'true') : null })} />
          ))}
        </fieldset>
      )}
      {groups.filter((g) => g.options.length > 0).map((g) => <Group key={g.param} group={g} />)}
    </div>
  )
}

function Group({ group: g }: { group: FilterGroup }) {
  const { params, update } = useFilters()
  const [more, setMore] = useState(false)
  const selected = params.getAll(g.param)
  const shown = more ? g.options : g.options.slice(0, 7)
  const set = (v: string, on: boolean) => update({ [g.param]: g.single ? (on ? v : null) : on ? [...selected, v] : selected.filter((x) => x !== v) })
  return (
    <fieldset className="flex flex-col gap-2.5">
      <legend className="eyebrow mb-3">{g.label}</legend>
      {shown.map((o) => (
        <Check key={o.value} label={o.label ?? o.value} count={o.count} checked={selected.includes(o.value)} onChange={(on) => set(o.value, on)} radio={g.single} name={g.param} />
      ))}
      {g.options.length > 7 && (
        <button type="button" onClick={() => setMore(!more)} className="focus-ring w-fit text-meta text-muted underline-offset-4 hover:text-text hover:underline">
          {more ? 'Show fewer' : `Show all ${g.options.length}`}
        </button>
      )}
    </fieldset>
  )
}

function Check({ label, count, checked, onChange, radio, name }: { label: string; count?: number; checked: boolean; onChange: (on: boolean) => void; radio?: boolean; name?: string }) {
  return (
    <label className="group flex cursor-pointer items-center gap-2.5 text-[0.9rem] text-text-2 hover:text-text">
      <input type={radio ? 'radio' : 'checkbox'} name={name} checked={checked} onChange={(e) => onChange(radio ? !checked : e.target.checked)} onClick={radio && checked ? () => onChange(false) : undefined}
        className="focus-ring size-4 shrink-0 cursor-pointer accent-[var(--accent)]" />
      <span className="min-w-0 flex-1 truncate">{label}</span>
      {count !== undefined && <span className="font-mono text-[0.7rem] text-faint tabular-nums">{count.toLocaleString()}</span>}
    </label>
  )
}
