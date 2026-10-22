'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { motion } from 'motion/react'
import { Info, Monitor, Moon, RotateCcw, Smartphone, Sun, Tablet } from 'lucide-react'
import { defaults, MSG, snippet, validateConfig, validateValue, type Config, type Control, type FrameMessage, type PlaygroundSchema } from '@/playground/schema'
import { spring } from '@/lib/motion/tokens'
import { cn } from '@/lib/cn'
import { CodeBlock } from '../kit/code-block'

const VIEWPORTS = [
  { key: 'full', label: 'Full width', icon: Monitor, width: '100%' },
  { key: 'tablet', label: 'Tablet', icon: Tablet, width: '768px' },
  { key: 'phone', label: 'Phone', icon: Smartphone, width: '375px' },
] as const

const SOURCE_LABEL: Record<string, string> = { documented: 'documented default', implementation: 'library default', preview: 'preview sample' }

/**
 * Interactive playground. Controls are generated from the component's schema; every change is validated here and again
 * inside the isolated preview frame, which re-renders the real component (or the labelled adapter). State is local to
 * this instance, so nothing leaks between components or systems.
 */
export function Playground({ schema }: { schema: PlaygroundSchema }) {
  const initial = useMemo(() => defaults(schema), [schema])
  const [config, setConfig] = useState<Config>(initial)
  const [theme, setTheme] = useState<'light' | 'dark'>('light')
  const [viewport, setViewport] = useState<(typeof VIEWPORTS)[number]['key']>('full')
  const [ready, setReady] = useState(false)
  const [height, setHeight] = useState(320)
  const [frameError, setFrameError] = useState<string | null>(null)
  const frame = useRef<HTMLIFrameElement>(null)
  // fixed for the frame's lifetime: theme and props changes are messages, not reloads
  const [src] = useState(() => `/playground-frame?component=${schema.component_id}`)

  const send = useCallback((cfg: Config, th: string) => {
    frame.current?.contentWindow?.postMessage({ type: MSG.config, config: cfg, theme: th } satisfies FrameMessage, window.location.origin)
  }, [])

  useEffect(() => {
    const onMessage = (e: MessageEvent<FrameMessage>) => {
      if (e.origin !== window.location.origin || e.source !== frame.current?.contentWindow) return
      if (e.data?.type === MSG.ready) (setReady(true), setFrameError(null))
      if (e.data?.type === MSG.size && typeof e.data.height === 'number') setHeight(Math.min(Math.max(e.data.height, 240), 900))
      if (e.data?.type === MSG.error) setFrameError(String(e.data.message ?? 'The preview reported an error.').slice(0, 200))
    }
    window.addEventListener('message', onMessage)
    return () => window.removeEventListener('message', onMessage)
  }, [])

  useEffect(() => {
    if (ready) send(config, theme)
  }, [ready, config, theme, send])

  const set = (c: Control, v: unknown) => setConfig((prev) => validateConfig(schema, { ...prev, [c.name]: validateValue(c, v) }))
  const changed = JSON.stringify(config) !== JSON.stringify(initial)
  const code = snippet(schema, config)
  const props = schema.controls.filter((c) => c.provenance !== 'preview')
  const content = schema.controls.filter((c) => c.provenance === 'preview')

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
      <div className="flex min-w-0 flex-col gap-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div role="radiogroup" aria-label="Preview width" className="flex rounded-sm border border-line-strong p-1">
            {VIEWPORTS.map((v) => (
              <button key={v.key} type="button" role="radio" aria-checked={viewport === v.key} aria-label={v.label} title={v.label} onClick={() => setViewport(v.key)}
                className={cn('focus-ring relative grid size-8 place-items-center rounded-xs', viewport === v.key ? 'text-accent-ink' : 'text-muted hover:text-text')}>
                {viewport === v.key && <motion.span layoutId="pg-vp" className="absolute inset-0 rounded-xs bg-accent" transition={spring.snappy} />}
                <v.icon className="relative size-4" aria-hidden />
              </button>
            ))}
          </div>
          {schema.themes.length > 1 && (
            <div role="radiogroup" aria-label="Preview theme" className="flex rounded-sm border border-line-strong p-1">
              {(['light', 'dark'] as const).filter((t) => schema.themes.includes(t)).map((t) => (
                <button key={t} type="button" role="radio" aria-checked={theme === t} onClick={() => setTheme(t)}
                  className={cn('focus-ring relative inline-flex h-8 items-center gap-1.5 rounded-xs px-3 text-meta', theme === t ? 'text-accent-ink' : 'text-muted hover:text-text')}>
                  {theme === t && <motion.span layoutId="pg-theme" className="absolute inset-0 rounded-xs bg-accent" transition={spring.snappy} />}
                  {t === 'light' ? <Sun className="relative size-3.5" aria-hidden /> : <Moon className="relative size-3.5" aria-hidden />}<span className="relative capitalize">{t}</span>
                </button>
              ))}
            </div>
          )}
        </div>
        <div className="overflow-hidden rounded-md border border-line bg-[repeating-conic-gradient(var(--surface)_0_25%,var(--bg-2)_0_50%)] bg-[length:16px_16px] p-3">
          <div className="mx-auto transition-[width] duration-300" style={{ width: VIEWPORTS.find((v) => v.key === viewport)!.width, maxWidth: '100%' }}>
            <iframe ref={frame} title={`${schema.component} preview`} src={src}
              sandbox="allow-scripts allow-same-origin" referrerPolicy="same-origin" loading="lazy"
              className="block w-full rounded-sm border-0" style={{ height, background: theme === 'dark' ? '#141414' : '#fff' }} />
          </div>
        </div>
        {frameError && <p role="status" className="text-meta text-danger">{frameError}</p>}
        <p className="flex items-start gap-2 text-[0.75rem] text-muted">
          <Info className="mt-0.5 size-3.5 shrink-0" aria-hidden />
          {schema.tier === 'live'
            ? <>Rendered by the real <span className="font-mono text-text-2">{schema.implementation?.package}@{schema.implementation?.version}</span> package — the version the documentation describes. {schema.implementation?.headless && schema.implementation.styling}</>
            : <>Platform-rendered preview, not the original source component. {schema.implementation?.styling}</>}
        </p>
        <div className="grid gap-4 lg:grid-cols-2">
          <CodeBlock code={JSON.stringify(config, null, 2)} label="Active configuration" />
          {code ? <CodeBlock code={code} label="Example derived from the documented API" /> : (
            <p className="rounded-sm border border-line p-4 text-meta text-muted">No import snippet: this preview is not the system&apos;s own package. The configuration describes the settings shown.</p>
          )}
        </div>
      </div>

      <aside aria-label="Properties" className="flex flex-col gap-5 rounded-md border border-line bg-surface/40 p-5 xl:sticky xl:top-[calc(var(--header-h)+4.5rem)] xl:max-h-[calc(100svh-var(--header-h)-6rem)] xl:self-start xl:overflow-y-auto">
        <div className="flex items-center justify-between gap-3">
          <p className="text-card font-medium">Properties</p>
          <button type="button" onClick={() => setConfig(initial)} disabled={!changed}
            className="focus-ring inline-flex h-8 items-center gap-1.5 rounded-sm px-2.5 text-meta text-muted hover:bg-surface-2 hover:text-text disabled:opacity-40">
            <RotateCcw className="size-3.5" aria-hidden />Reset
          </button>
        </div>
        {props.length === 0 && <p className="text-meta text-muted">No documented properties can be varied safely in the preview.</p>}
        {props.map((c) => <ControlField key={c.name} c={c} value={config[c.name]} onChange={(v) => set(c, v)} />)}
        {content.length > 0 && (
          <fieldset className="flex flex-col gap-4 border-t border-line pt-5">
            <legend className="eyebrow mb-3">Sample content</legend>
            {content.map((c) => <ControlField key={c.name} c={c} value={config[c.name]} onChange={(v) => set(c, v)} />)}
          </fieldset>
        )}
        {!!schema.metadata_only_count && (
          <details className="border-t border-line pt-4 text-meta text-muted">
            <summary className="cursor-pointer">{schema.metadata_only_count} more documented props aren&apos;t adjustable here</summary>
            <p className="mt-2">Handlers, render props, objects and open types can&apos;t be varied safely; they&apos;re listed in the API table: <span className="font-mono text-[0.7rem]">{schema.metadata_only_props?.slice(0, 24).join(', ')}</span></p>
          </details>
        )}
      </aside>
    </div>
  )
}

function ControlField({ c, value, onChange }: { c: Control; value: unknown; onChange: (v: unknown) => void }) {
  const id = `pg-${c.name}`
  const hint = [c.type_text && c.kind !== 'string' ? c.type_text : null, c.default !== undefined && c.default !== null && c.default_source ? `${SOURCE_LABEL[c.default_source]}: ${String(c.default)}` : null,
    c.documented_default_text ? `documented default: ${c.documented_default_text}` : null].filter(Boolean)
  const label = (
    <span className="flex items-baseline justify-between gap-2">
      <span className="font-mono text-[0.8rem] text-text">{c.name}</span>
      {c.provenance === 'implementation' && <span className="text-[0.68rem] text-faint" title="Accepted by the installed package; the collected docs don't list its values">package</span>}
    </span>
  )
  const desc = (c.description || hint.length > 0) && (
    <span id={`${id}-d`} className="block text-[0.72rem] leading-snug text-muted">{c.description && <span className="line-clamp-2">{c.description}</span>}{hint.length > 0 && <span className="block font-mono text-[0.66rem] text-faint">{hint.join(' · ')}</span>}</span>
  )
  const field = 'focus-ring h-9 w-full rounded-sm border border-line-strong bg-bg px-2.5 text-[0.88rem] text-text focus:border-accent focus:outline-none'
  if (c.kind === 'boolean') {
    return (
      <label htmlFor={id} className="flex cursor-pointer items-start justify-between gap-3">
        <span className="min-w-0 flex-1">{label}{desc}</span>
        <input id={id} type="checkbox" role="switch" aria-describedby={`${id}-d`} checked={value === true} onChange={(e) => onChange(e.target.checked)} className="focus-ring mt-1 size-4 accent-[var(--accent)]" />
      </label>
    )
  }
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} id={`${id}-label`}>{label}</label>
      {c.kind === 'enum' ? (
        (c.options?.length ?? 0) <= 4 ? (
          <div role="radiogroup" aria-labelledby={`${id}-label`} aria-describedby={`${id}-d`} id={id} className="flex flex-wrap gap-1">
            {c.options!.map((o) => (
              <button key={o} type="button" role="radio" aria-checked={value === o} onClick={() => onChange(value === o ? undefined : o)}
                className={cn('focus-ring h-8 rounded-xs border px-2.5 font-mono text-[0.72rem]', value === o ? 'border-accent bg-accent-soft text-text' : 'border-line-strong text-text-2 hover:text-text')}>{o}</button>
            ))}
          </div>
        ) : (
          <select id={id} value={(value as string) ?? ''} onChange={(e) => onChange(e.target.value || undefined)} aria-describedby={`${id}-d`} className={field}>
            <option value="">— component default —</option>
            {c.options!.map((o) => <option key={o} value={o}>{o}</option>)}
          </select>
        )
      ) : c.kind === 'number' ? (
        <input id={id} type="number" inputMode="decimal" value={(value as number) ?? ''} min={c.min} max={c.max} step={c.step} aria-describedby={`${id}-d`}
          onChange={(e) => onChange(e.target.value === '' ? undefined : Number(e.target.value))} className={field} />
      ) : (
        <input id={id} type="text" value={(value as string) ?? ''} maxLength={c.max_length ?? 120} aria-describedby={`${id}-d`} onChange={(e) => onChange(e.target.value)} className={field} />
      )}
      {desc}
    </div>
  )
}
