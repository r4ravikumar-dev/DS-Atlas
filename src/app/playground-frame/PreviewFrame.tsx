'use client'

import { Component as ReactComponent, useEffect, useMemo, useRef, useState, type ComponentType } from 'react'
import { useSearchParams } from 'next/navigation'
import { api } from '@/lib/api/client'
import type { Item, Page, Token } from '@/lib/api/types'
import { defaults, MSG, split, validateConfig, type Config, type FrameMessage, type PlaygroundSchema } from '@/playground/schema'
import type { RenderProps } from '@/playground/libs/types'

/** Each library is its own chunk, loaded only when its preview is shown — and only inside this frame. */
const LIBS: Record<string, () => Promise<{ default: ComponentType<RenderProps> }>> = {
  mantine: () => import('@/playground/libs/mantine'),
  antd: () => import('@/playground/libs/antd'),
  'react-aria': () => import('@/playground/libs/react-aria'),
  'base-ui': () => import('@/playground/libs/base-ui'),
  radix: () => import('@/playground/libs/radix'),
  shadcn: () => import('@/playground/libs/shadcn'),
}

/**
 * The component preview document. Embedded same-origin by the playground page, which sends configurations with
 * postMessage. Every message is checked for origin and source and re-validated against the schema this frame fetched
 * itself; only validated props reach the component. No code is ever received or evaluated.
 */
export function PreviewFrame() {
  const sp = useSearchParams()
  const id = Number(sp.get('component'))
  const [schema, setSchema] = useState<PlaygroundSchema | null>(null)
  const [Renderer, setRenderer] = useState<ComponentType<RenderProps> | null>(null)
  const [tokens, setTokens] = useState<RenderProps['tokens']>([])
  const [config, setConfig] = useState<Config>({})
  const [theme, setTheme] = useState<'light' | 'dark'>(sp.get('theme') === 'dark' ? 'dark' : 'light')
  const [error, setError] = useState<string | null>(null)
  const root = useRef<HTMLDivElement>(null)

  const post = (m: FrameMessage) => window.parent !== window && window.parent.postMessage(m, window.location.origin)

  useEffect(() => {
    if (!Number.isInteger(id) || id < 1) return setError('No component selected.')
    let alive = true
    ;(async () => {
      try {
        const s = (await api<Item<PlaygroundSchema>>(`/components/${id}/playground-schema`)).data
        const load = s.implementation && LIBS[s.implementation.library_key]
        if (!load || s.tier === 'docs') throw new Error('This component has no interactive preview.')
        const [mod, toks] = await Promise.all([
          load(),
          s.tier === 'adapter' && s.system_id
            ? Promise.all([1, 2].map((page) => api<Page<Token>>(`/design-systems/${s.system_id}/tokens`, { query: { page, page_size: 100 } }).then((r) => r.data).catch(() => [])))
            : Promise.resolve([]),
        ])
        if (!alive) return
        setTokens(toks.flat().map((t) => ({ path: t.path, theme: t.theme, value: (t.resolved_value ?? t.raw_value ?? '').trim() })))
        setSchema(s)
        setConfig(defaults(s))
        setRenderer(() => mod.default)
        post({ type: MSG.ready })
      } catch (e) {
        if (alive) setError(e instanceof Error ? e.message : 'The preview could not be loaded.')
      }
    })()
    return () => { alive = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  useEffect(() => {
    const onMessage = (e: MessageEvent<FrameMessage>) => {
      if (e.origin !== window.location.origin || e.source !== window.parent || !schema) return
      if (e.data?.type !== MSG.config) return
      setConfig(validateConfig(schema, e.data.config))
      if (e.data.theme === 'light' || e.data.theme === 'dark') setTheme(e.data.theme)
    }
    window.addEventListener('message', onMessage)
    return () => window.removeEventListener('message', onMessage)
  }, [schema])

  useEffect(() => {
    if (error) post({ type: MSG.error, message: error })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [error])

  useEffect(() => {
    const el = root.current
    if (!el) return
    const ro = new ResizeObserver(() => post({ type: MSG.size, height: Math.ceil(el.getBoundingClientRect().height) }))
    ro.observe(el)
    return () => ro.disconnect()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [Renderer])

  const parts = useMemo(() => (schema ? split(schema, config) : { props: {}, content: {} }), [schema, config])
  const bg = theme === 'dark' ? '#141414' : '#ffffff'

  return (
    <div ref={root} style={{ minHeight: 240, display: 'grid', placeItems: 'center', padding: 32, background: bg, colorScheme: theme }} data-preview-theme={theme}>
      {error ? <p role="alert" style={{ font: '14px system-ui', color: theme === 'dark' ? '#ccc' : '#444' }}>{error}</p>
        : !Renderer || !schema ? <p style={{ font: '13px system-ui', color: '#888' }}>Loading preview…</p>
        : (
          <Boundary key={JSON.stringify(parts) + theme} onError={(m) => post({ type: MSG.error, message: m })}>
            <Renderer impl={schema.implementation!.key.split('.').slice(1).join('.')} props={parts.props} content={parts.content} theme={theme} tokens={tokens} />
          </Boundary>
        )}
    </div>
  )
}

/** A configuration the component rejects shows a message instead of breaking the frame. */
class Boundary extends ReactComponent<{ children: React.ReactNode; onError: (m: string) => void }, { failed: boolean }> {
  state = { failed: false }
  static getDerivedStateFromError() {
    return { failed: true }
  }
  componentDidCatch(e: Error) {
    this.props.onError(e.message)
  }
  render() {
    return this.state.failed ? <p role="alert" style={{ font: '14px system-ui', color: '#b91c1c' }}>This combination of properties could not be rendered.</p> : this.props.children
  }
}
