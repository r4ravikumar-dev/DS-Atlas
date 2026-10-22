/**
 * Playground schema (from GET /components/{id}/playground-schema) and the validation applied to every configuration,
 * both in the controls panel and again inside the preview frame. Only schema-listed properties of the right kind ever
 * reach a component; anything else is dropped.
 */
export type ControlKind = 'boolean' | 'enum' | 'number' | 'string'
export type DefaultSource = 'documented' | 'implementation' | 'preview' | null

export interface Control {
  name: string
  kind: ControlKind
  options?: string[]
  min?: number
  max?: number
  step?: number
  max_length?: number
  description?: string | null
  type_text?: string | null
  documented: boolean
  provenance: 'documented' | 'implementation' | 'preview'
  default?: unknown
  default_source: DefaultSource
  documented_default_text?: string | null
  required?: boolean
}

export interface PlaygroundSchema {
  component_id: number
  component: string
  library: string | null
  system_id: number | null
  system_slug?: string | null
  slug?: string | null
  documentation_url: string | null
  tier: 'live' | 'adapter' | 'docs'
  implementation: { key: string; library_key: string; package: string | null; version: string | null; styling: string; headless: boolean } | null
  controls: Control[]
  themes: string[]
  states: string[]
  limitations: string[]
  metadata_only_props?: string[]
  metadata_only_count?: number
  documented_props?: number
}

export type Config = Record<string, string | number | boolean | undefined>

const CONTROL_CHARS = /[\u0000-\u001f\u007f]/g

/** Coerce one value to the control's kind, or undefined when it doesn't fit (never throws). */
export function validateValue(c: Control, v: unknown): string | number | boolean | undefined {
  if (v === undefined || v === null || v === '') return undefined
  switch (c.kind) {
    case 'boolean':
      return typeof v === 'boolean' ? v : undefined
    case 'enum':
      return typeof v === 'string' && (c.options ?? []).includes(v) ? v : undefined
    case 'number': {
      const n = typeof v === 'number' ? v : Number(v)
      if (!Number.isFinite(n)) return undefined
      return Math.min(c.max ?? 1e6, Math.max(c.min ?? -1e6, n))
    }
    case 'string':
      return typeof v === 'string' ? v.replace(CONTROL_CHARS, '').slice(0, c.max_length ?? 120) : undefined
  }
}

export function validateConfig(schema: Pick<PlaygroundSchema, 'controls'>, input: unknown): Config {
  const src = input && typeof input === 'object' ? (input as Record<string, unknown>) : {}
  const out: Config = {}
  for (const c of schema.controls) {
    const v = validateValue(c, src[c.name])
    if (v !== undefined) out[c.name] = v
  }
  return out
}

/** Initial configuration: documented, implementation or preview defaults — whichever the schema states, nothing invented. */
export function defaults(schema: Pick<PlaygroundSchema, 'controls'>): Config {
  return validateConfig(schema, Object.fromEntries(schema.controls.map((c) => [c.name, c.default])))
}

/** Split a validated configuration into component props and preview content (labels, titles). */
export function split(schema: Pick<PlaygroundSchema, 'controls'>, config: Config) {
  const props: Record<string, unknown> = {}
  const content: Record<string, string> = {}
  for (const c of schema.controls) {
    if (config[c.name] === undefined) continue
    if (c.provenance === 'preview') content[c.name] = String(config[c.name])
    else props[c.name] = config[c.name]
  }
  return { props, content }
}

export const MSG = { config: 'dsrp-playground:config', ready: 'dsrp-playground:ready', size: 'dsrp-playground:size', error: 'dsrp-playground:error' } as const
export interface FrameMessage { type: (typeof MSG)[keyof typeof MSG]; config?: Config; theme?: string; height?: number; message?: string }

/** A JSX-like snippet of the active configuration for live implementations (real package, real export name). */
export function snippet(schema: PlaygroundSchema, config: Config): string | null {
  const impl = schema.implementation
  if (!impl || schema.tier !== 'live' || !impl.package) return null
  const name = impl.key.split('.').slice(1).join('.')
  const { props, content } = split(schema, config)
  const attrs = Object.entries(props).map(([k, v]) => (v === true ? k : typeof v === 'string' ? `${k}="${v.replace(/"/g, '&quot;')}"` : `${k}={${JSON.stringify(v)}}`))
  const children = content.children
  const extra = Object.entries(content).filter(([k]) => k !== 'children').map(([k, v]) => `${k}="${v.replace(/"/g, '&quot;')}"`)
  const all = [...attrs, ...extra]
  const open = `<${name}${all.length ? ' ' + all.join(' ') : ''}`
  return `import { ${name.split('.')[0]} } from '${impl.package}'\n\n${children ? `${open}>${children}</${name}>` : `${open} />`}`
}
