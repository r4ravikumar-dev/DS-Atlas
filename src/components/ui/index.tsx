'use client'

import { cloneElement, forwardRef, useEffect, useId, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import Link from 'next/link'
import { AnimatePresence, motion } from 'framer-motion'
import { AlertTriangle, Check, ChevronDown, ChevronLeft, ChevronRight, ExternalLink, Inbox, Loader2, Search, X } from 'lucide-react'
import { ApiError } from '@/lib/api/client'
import type { Facet, JobStatus, VerificationStatus } from '@/lib/api/types'
import s from './ui.module.scss'

/* ───────────── Buttons ───────────── */
type BtnProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  size?: 'sm' | 'md'
  loading?: boolean
  icon?: React.ReactNode
}
export const Button = forwardRef<HTMLButtonElement, BtnProps>(function Button(
  { variant = 'secondary', size = 'md', loading, icon, children, className, disabled, ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      className={`${s.btn} ${s[variant]} ${s[size]} ${className ?? ''}`}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...rest}
    >
      {loading ? <Loader2 size={15} className={s.spin} aria-hidden /> : icon}
      {children}
    </button>
  )
})

export function ExtLink({ href, children, className }: { href?: string | null; children?: React.ReactNode; className?: string }) {
  if (!href) return <Missing />
  return (
    <a href={href} target="_blank" rel="noopener noreferrer nofollow" className={`${s.ext} ${className ?? ''}`}>
      {children ?? prettyUrl(href)}
      <ExternalLink size={12} aria-hidden />
      <span className="sr-only">(opens in new tab)</span>
    </a>
  )
}

export function prettyUrl(u: string) {
  try {
    const x = new URL(u)
    return (x.host + x.pathname).replace(/\/$/, '')
  } catch {
    return u
  }
}

/* ───────────── Status & badges ───────────── */
const VERIFY_LABEL: Record<string, string> = { verified: 'Verified', partially_verified: 'Partially verified', unverified: 'Unverified' }
const VERIFY_HINT: Record<string, string> = {
  verified: 'Read from the official source.',
  partially_verified: 'Corroborated by ≥2 independent sources, official docs not inspected.',
  unverified: 'Single third-party claim.',
}
export function VerifyBadge({ status }: { status: VerificationStatus | string }) {
  return (
    <span className={`${s.badge} ${s['v_' + status]}`} title={VERIFY_HINT[status]}>
      <i aria-hidden />
      {VERIFY_LABEL[status] ?? status}
    </span>
  )
}

const JOB_LABEL: Record<string, string> = {
  queued: 'Queued',
  running: 'Running',
  succeeded: 'Succeeded',
  partially_succeeded: 'Partial',
  failed: 'Failed',
  cancelled: 'Cancelled',
}
export function JobBadge({ status }: { status: JobStatus | string }) {
  return (
    <span className={`${s.badge} ${s['j_' + status]}`}>
      {status === 'running' ? <Loader2 size={11} className={s.spin} aria-hidden /> : <i aria-hidden />}
      {JOB_LABEL[status] ?? status}
    </span>
  )
}

export function SourceStatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    inspected: 'j_succeeded',
    inspected_partial: 'j_partially_succeeded',
    unavailable_seed__substitute_extracted: 'j_failed',
    never_crawled: 'j_cancelled',
  }
  const label: Record<string, string> = {
    inspected: 'Inspected',
    inspected_partial: 'Partially inspected',
    unavailable_seed__substitute_extracted: 'Unavailable · substitute used',
    never_crawled: 'Never crawled',
  }
  return (
    <span className={`${s.badge} ${s[map[status] ?? 'j_failed']}`}>
      <i aria-hidden />
      {label[status] ?? status.replace(/_/g, ' ')}
    </span>
  )
}

export function Tag({ children, tone }: { children: React.ReactNode; tone?: 'accent' | 'muted' }) {
  return <span className={`${s.tag} ${tone ? s['t_' + tone] : ''}`}>{children}</span>
}

export function Missing({ label = 'Not documented' }: { label?: string }) {
  return (
    <span className={s.missing} title="No value in the inspected sources (unknown, not necessarily absent).">
      {label}
    </span>
  )
}

/* ───────────── Loading / empty / error ───────────── */
export function Skeleton({ h = 16, w = '100%', r = 6 }: { h?: number; w?: number | string; r?: number }) {
  return <span className={s.skeleton} style={{ height: h, width: w, borderRadius: r }} aria-hidden />
}

export function SkeletonRows({ rows = 6, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <div className={s.skelRows} role="status" aria-label="Loading">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} style={{ gridTemplateColumns: `repeat(${cols}, 1fr)` }}>
          {Array.from({ length: cols }, (_, j) => (
            <Skeleton key={j} h={14} w={`${60 + ((i * 7 + j * 13) % 35)}%`} />
          ))}
        </div>
      ))}
    </div>
  )
}

export function EmptyState({ title, children, action }: { title: string; children?: React.ReactNode; action?: React.ReactNode }) {
  return (
    <div className={s.empty}>
      <Inbox size={22} aria-hidden />
      <strong>{title}</strong>
      {children && <p>{children}</p>}
      {action}
    </div>
  )
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const e = error instanceof ApiError ? error : null
  return (
    <div className={s.error} role="alert">
      <AlertTriangle size={20} aria-hidden />
      <div>
        <strong>{e?.status === 403 ? 'You do not have access to this' : e?.status === 404 ? 'Not found' : 'Something went wrong'}</strong>
        <p>{(error as Error)?.message ?? 'Unknown error'}</p>
        {e?.requestId && <small>Request ID: {e.requestId}</small>}
      </div>
      {onRetry && (
        <Button size="sm" onClick={onRetry}>
          Retry
        </Button>
      )}
    </div>
  )
}

/* ───────────── Inputs ───────────── */
export function SearchInput({
  value,
  onChange,
  placeholder = 'Search…',
  delay = 300,
  label = 'Search',
}: {
  value: string
  onChange: (v: string) => void
  placeholder?: string
  delay?: number
  label?: string
}) {
  const [local, setLocal] = useState(value)
  const first = useRef(true)
  useEffect(() => setLocal(value), [value])
  useEffect(() => {
    if (first.current) {
      first.current = false
      return
    }
    const t = setTimeout(() => local !== value && onChange(local), delay)
    return () => clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [local])
  return (
    <label className={s.search}>
      <Search size={16} aria-hidden />
      <span className="sr-only">{label}</span>
      <input value={local} onChange={(e) => setLocal(e.target.value)} placeholder={placeholder} type="search" maxLength={200} />
      {local && (
        <button type="button" onClick={() => (setLocal(''), onChange(''))} aria-label="Clear search">
          <X size={14} />
        </button>
      )}
    </label>
  )
}

export function FacetFilter({
  label,
  facets,
  selected,
  onChange,
  format = (v) => v,
}: {
  label: string
  facets: Facet[] | undefined
  selected: string[]
  onChange: (v: string[]) => void
  format?: (v: string) => string
}) {
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState('')
  const ref = useRef<HTMLDivElement>(null)
  const id = useId()
  useEffect(() => {
    const close = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && setOpen(false)
    const esc = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false)
    document.addEventListener('mousedown', close)
    document.addEventListener('keydown', esc)
    return () => (document.removeEventListener('mousedown', close), document.removeEventListener('keydown', esc))
  }, [])
  const list = (facets ?? []).filter((f) => !q || format(f.value).toLowerCase().includes(q.toLowerCase()))
  return (
    <div className={s.facet} ref={ref}>
      <button type="button" className={s.facetBtn} aria-expanded={open} aria-controls={id} onClick={() => setOpen((o) => !o)} data-active={selected.length > 0 || undefined}>
        {label}
        {selected.length > 0 && <span className={s.count}>{selected.length}</span>}
        <ChevronDown size={14} aria-hidden />
      </button>
      {open && (
        <div className={s.facetMenu} id={id} role="group" aria-label={label}>
          {(facets?.length ?? 0) > 8 && <input className={s.facetSearch} value={q} onChange={(e) => setQ(e.target.value)} placeholder={`Filter ${label.toLowerCase()}…`} aria-label={`Filter ${label}`} />}
          {!facets && <Skeleton h={80} />}
          {facets && list.length === 0 && <p className={s.facetEmpty}>No options</p>}
          <div className={s.facetList}>
            {list.map((f) => {
              const on = selected.includes(f.value)
              return (
                <label key={f.value} className={s.facetOpt}>
                  <input type="checkbox" checked={on} onChange={() => onChange(on ? selected.filter((x) => x !== f.value) : [...selected, f.value])} />
                  <span>{format(f.value)}</span>
                  <small>{f.count.toLocaleString()}</small>
                </label>
              )
            })}
          </div>
          {selected.length > 0 && (
            <button type="button" className={s.facetClear} onClick={() => onChange([])}>
              Clear
            </button>
          )}
        </div>
      )}
    </div>
  )
}

export function Select({ label, value, onChange, options }: { label: string; value: string; onChange: (v: string) => void; options: { value: string; label: string }[] }) {
  return (
    <label className={s.select}>
      <span className="sr-only">{label}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)} aria-label={label}>
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      <ChevronDown size={14} aria-hidden />
    </label>
  )
}

export function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <button type="button" className={s.toggle} aria-pressed={checked} onClick={() => onChange(!checked)}>
      <span className={s.box}>{checked && <Check size={11} strokeWidth={3} />}</span>
      {label}
    </button>
  )
}

export function Field({ label, error, hint, children }: { label: string; error?: string; hint?: string; children: React.ReactElement }) {
  const id = useId()
  return (
    <div className={s.field} data-invalid={error ? true : undefined}>
      <label htmlFor={id}>{label}</label>
      {cloneElement(children as React.ReactElement<Record<string, unknown>>, { id, 'aria-invalid': !!error || undefined, 'aria-describedby': error || hint ? `${id}-d` : undefined })}
      {(error || hint) && (
        <small id={`${id}-d`} className={error ? s.fieldErr : undefined}>
          {error ?? hint}
        </small>
      )}
    </div>
  )
}

/* ───────────── Pagination ───────────── */
export function Pagination({ page, totalPages, total, onPage, pageSize }: { page: number; totalPages: number; total: number; onPage: (p: number) => void; pageSize: number }) {
  if (total === 0) return null
  const from = (page - 1) * pageSize + 1
  const to = Math.min(total, page * pageSize)
  return (
    <nav className={s.pager} aria-label="Pagination">
      <span>
        {from.toLocaleString()}–{to.toLocaleString()} of <strong>{total.toLocaleString()}</strong>
      </span>
      <div>
        <Button size="sm" variant="ghost" onClick={() => onPage(page - 1)} disabled={page <= 1} aria-label="Previous page" icon={<ChevronLeft size={15} />} />
        <span aria-current="page">
          {page} / {totalPages}
        </span>
        <Button size="sm" variant="ghost" onClick={() => onPage(page + 1)} disabled={page >= totalPages} aria-label="Next page" icon={<ChevronRight size={15} />} />
      </div>
    </nav>
  )
}

/* ───────────── Layout pieces ───────────── */
export function PageHeader({ title, description, actions, crumbs }: { title: React.ReactNode; description?: React.ReactNode; actions?: React.ReactNode; crumbs?: { href: string; label: string }[] }) {
  return (
    <header className={s.pageHeader}>
      {crumbs && (
        <nav aria-label="Breadcrumb" className={s.crumbs}>
          {crumbs.map((c) => (
            <span key={c.href}>
              <Link href={c.href}>{c.label}</Link> /
            </span>
          ))}
        </nav>
      )}
      <div className={s.phRow}>
        <div>
          <h1>{title}</h1>
          {description && <p>{description}</p>}
        </div>
        {actions && <div className={s.phActions}>{actions}</div>}
      </div>
    </header>
  )
}

export function Panel({ title, actions, children, className, id }: { title?: React.ReactNode; actions?: React.ReactNode; children: React.ReactNode; className?: string; id?: string }) {
  return (
    <section className={`${s.panel} ${className ?? ''}`} id={id} aria-label={typeof title === 'string' ? title : undefined}>
      {(title || actions) && (
        <header>
          {title && <h2>{title}</h2>}
          {actions}
        </header>
      )}
      {children}
    </section>
  )
}

export function Stat({ label, value, hint, href, tone }: { label: string; value: React.ReactNode; hint?: React.ReactNode; href?: string; tone?: 'warn' | 'bad' | 'good' }) {
  const body = (
    <>
      <span className={s.statLabel}>{label}</span>
      <strong className={s.statValue}>{value}</strong>
      {hint && <span className={s.statHint}>{hint}</span>}
    </>
  )
  return href ? (
    <Link href={href} className={`${s.stat} ${tone ? s['tone_' + tone] : ''}`}>
      {body}
    </Link>
  ) : (
    <div className={`${s.stat} ${tone ? s['tone_' + tone] : ''}`}>{body}</div>
  )
}

export function KV({ items }: { items: [string, React.ReactNode][] }) {
  return (
    <dl className={s.kv}>
      {items.map(([k, v]) => (
        <div key={k}>
          <dt>{k}</dt>
          <dd>{v === null || v === undefined || v === '' || (Array.isArray(v) && v.length === 0) ? <Missing /> : v}</dd>
        </div>
      ))}
    </dl>
  )
}

export function Tabs<T extends string>({ tabs, value, onChange }: { tabs: { value: T; label: string; count?: number }[]; value: T; onChange: (v: T) => void }) {
  return (
    <div className={s.tabs} role="tablist">
      {tabs.map((t) => (
        <button key={t.value} role="tab" aria-selected={value === t.value} onClick={() => onChange(t.value)} type="button">
          {value === t.value && <motion.span layoutId={`tab-${tabs.map((x) => x.value).join()}`} className={s.tabPill} />}
          <span>
            {t.label}
            {t.count !== undefined && <small>{t.count.toLocaleString()}</small>}
          </span>
        </button>
      ))}
    </div>
  )
}

export function Drawer({ open, onClose, title, children }: { open: boolean; onClose: () => void; title: string; children: React.ReactNode }) {
  const [mounted, setMounted] = useState(false)
  useEffect(() => setMounted(true), [])
  useEffect(() => {
    if (!open) return
    const k = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', k)
    return () => window.removeEventListener('keydown', k)
  }, [open, onClose])
  if (!mounted) return null
  return createPortal(
    <AnimatePresence>
      {open && (
        <>
          <motion.div className={s.scrim} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose} />
          <motion.aside
            className={s.drawer}
            role="dialog"
            aria-modal="true"
            aria-label={title}
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', stiffness: 300, damping: 34 }}
          >
            <header>
              <h2>{title}</h2>
              <button onClick={onClose} aria-label="Close" autoFocus>
                <X size={18} />
              </button>
            </header>
            <div className={s.drawerBody}>{children}</div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>,
    document.body,
  )
}

export function ConfirmDialog({ open, title, body, confirmLabel = 'Confirm', danger, onConfirm, onCancel, loading }: {
  open: boolean
  title: string
  body: React.ReactNode
  confirmLabel?: string
  danger?: boolean
  onConfirm: () => void
  onCancel: () => void
  loading?: boolean
}) {
  const [mounted, setMounted] = useState(false)
  useEffect(() => setMounted(true), [])
  if (!mounted || !open) return null
  return createPortal(
    <div className={s.modalWrap} role="presentation" onMouseDown={(e) => e.target === e.currentTarget && onCancel()}>
      <div className={s.modal} role="alertdialog" aria-modal="true" aria-labelledby="cd-title">
        <h2 id="cd-title">{title}</h2>
        <div>{body}</div>
        <footer>
          <Button variant="ghost" onClick={onCancel} autoFocus>
            Cancel
          </Button>
          <Button variant={danger ? 'danger' : 'primary'} onClick={onConfirm} loading={loading}>
            {confirmLabel}
          </Button>
        </footer>
      </div>
    </div>,
    document.body,
  )
}

export function Progress({ value, max }: { value: number; max: number }) {
  const pct = max > 0 ? Math.min(100, Math.round((value / max) * 100)) : 0
  return (
    <div className={s.progress} role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
      <i style={{ width: `${pct}%` }} />
    </div>
  )
}

export function Bar({ label, value, max, hint }: { label: React.ReactNode; value: number; max: number; hint?: React.ReactNode }) {
  return (
    <div className={s.barRow}>
      <span className={s.barLabel}>{label}</span>
      <span className={s.barTrack}>
        <i style={{ width: `${max ? Math.max(1, (value / max) * 100) : 0}%` }} />
      </span>
      <span className={s.barVal}>{hint ?? value.toLocaleString()}</span>
    </div>
  )
}

export function fmtDate(d?: string | null, withTime = true) {
  if (!d) return '—'
  const x = new Date(d)
  return withTime ? x.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }) : x.toLocaleDateString(undefined, { dateStyle: 'medium' })
}

export function fmtAgo(d?: string | null) {
  if (!d) return 'never'
  const s = (Date.now() - new Date(d).getTime()) / 1000
  if (s < 60) return 'just now'
  if (s < 3600) return `${Math.round(s / 60)} min ago`
  if (s < 86400) return `${Math.round(s / 3600)} h ago`
  return `${Math.round(s / 86400)} d ago`
}

export function fmtDuration(a?: string | null, b?: string | null) {
  if (!a) return '—'
  const ms = (b ? new Date(b) : new Date()).getTime() - new Date(a).getTime()
  const s = Math.round(ms / 1000)
  return s < 60 ? `${s}s` : `${Math.floor(s / 60)}m ${s % 60}s`
}
