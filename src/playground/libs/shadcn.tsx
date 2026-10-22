'use client'

import { isColor } from '@/lib/tokens/preview'
import type { RenderProps } from './types'

/**
 * Platform-rendered adapter (tier B) for shadcn/ui. shadcn/ui is distributed as source you copy into a project, not as a
 * package, so its published component recipes (variants and sizes, MIT-licensed) are reproduced here as plain CSS and
 * coloured only with the shadcn/ui theme tokens stored for this system. Behaviour and accessibility parity are not claimed.
 */
const VARS = ['background', 'foreground', 'card', 'card-foreground', 'primary', 'primary-foreground', 'secondary', 'secondary-foreground',
  'muted', 'muted-foreground', 'accent', 'accent-foreground', 'destructive', 'border', 'input', 'ring', 'radius']
const DIM = /^-?\d*\.?\d+(rem|px|em)$/

function themeVars(tokens: RenderProps['tokens'], theme: string) {
  const out: Record<string, string> = {}
  for (const name of VARS) {
    const pick = (tokens ?? []).filter((t) => t.path === `--${name}`)
    const t = pick.find((x) => x.theme === theme) ?? pick.find((x) => !x.theme || x.theme === 'light')
    if (t && (isColor(t.value) || (name === 'radius' && DIM.test(t.value)))) out[`--${name}`] = t.value
  }
  return out
}

const CSS = `
.pg-shadcn { font: 14px/1.4 ui-sans-serif, system-ui, sans-serif; color: var(--foreground); background: var(--background); padding: 24px; border-radius: 12px; }
.pg-shadcn .btn { display: inline-flex; align-items: center; justify-content: center; gap: 8px; white-space: nowrap; border-radius: calc(var(--radius) - 2px); font-size: 14px; font-weight: 500; border: 1px solid transparent; cursor: pointer; transition: background-color .15s, color .15s; height: 36px; padding: 8px 16px; outline: none; }
.pg-shadcn .btn:focus-visible { box-shadow: 0 0 0 3px color-mix(in oklab, var(--ring) 50%, transparent); border-color: var(--ring); }
.pg-shadcn .btn.default { background: var(--primary); color: var(--primary-foreground); }
.pg-shadcn .btn.default:hover { background: color-mix(in oklab, var(--primary) 90%, transparent); }
.pg-shadcn .btn.destructive { background: var(--destructive); color: #fff; }
.pg-shadcn .btn.outline { background: var(--background); border-color: var(--border); box-shadow: 0 1px 2px rgb(0 0 0 / .05); }
.pg-shadcn .btn.outline:hover, .pg-shadcn .btn.ghost:hover { background: var(--accent); color: var(--accent-foreground); }
.pg-shadcn .btn.secondary { background: var(--secondary); color: var(--secondary-foreground); }
.pg-shadcn .btn.ghost { background: transparent; }
.pg-shadcn .btn.link { background: transparent; color: var(--primary); text-underline-offset: 4px; }
.pg-shadcn .btn.link:hover { text-decoration: underline; }
.pg-shadcn .btn.xs { height: 24px; padding: 0 8px; font-size: 12px; gap: 4px; }
.pg-shadcn .btn.sm { height: 32px; padding: 0 12px; gap: 6px; }
.pg-shadcn .btn.lg { height: 40px; padding: 0 24px; }
.pg-shadcn .btn.icon { width: 36px; padding: 0; } .pg-shadcn .btn.icon-xs { width: 24px; height: 24px; padding: 0; }
.pg-shadcn .btn.icon-sm { width: 32px; height: 32px; padding: 0; } .pg-shadcn .btn.icon-lg { width: 40px; height: 40px; padding: 0; }
.pg-shadcn .badge { display: inline-flex; align-items: center; border-radius: calc(var(--radius) - 2px); border: 1px solid transparent; padding: 2px 8px; font-size: 12px; font-weight: 500; }
.pg-shadcn .badge.default { background: var(--primary); color: var(--primary-foreground); }
.pg-shadcn .badge.secondary { background: var(--secondary); color: var(--secondary-foreground); }
.pg-shadcn .badge.destructive { background: var(--destructive); color: #fff; }
.pg-shadcn .badge.outline { border-color: var(--border); color: var(--foreground); }
.pg-shadcn .badge.ghost:hover { background: var(--accent); }
.pg-shadcn .badge.link { color: var(--primary); text-decoration: underline; text-underline-offset: 4px; }
.pg-shadcn .alert { width: 420px; border: 1px solid var(--border); border-radius: var(--radius); padding: 12px 16px; background: var(--card); color: var(--card-foreground); display: grid; gap: 2px; }
.pg-shadcn .alert.destructive { color: var(--destructive); }
.pg-shadcn .alert .title { font-weight: 500; } .pg-shadcn .alert .desc { color: var(--muted-foreground); } .pg-shadcn .alert.destructive .desc { color: color-mix(in oklab, var(--destructive) 90%, transparent); }
`

export default function ShadcnRenderer({ impl, props, content, theme, tokens }: RenderProps) {
  const variant = String(props.variant ?? 'default')
  const size = String(props.size ?? 'default')
  const vars = themeVars(tokens, theme)
  return (
    <div className="pg-shadcn" style={vars as React.CSSProperties}>
      <style>{CSS}</style>
      {impl === 'Button' && <button type="button" className={`btn ${variant} ${size === 'default' ? '' : size}`}>{size.startsWith('icon') ? '★' : content.children}</button>}
      {impl === 'Badge' && <span className={`badge ${variant}`}>{content.children}</span>}
      {impl === 'Alert' && <div role="alert" className={`alert ${variant}`}><div className="title">{content.title}</div><div className="desc">{content.description}</div></div>}
    </div>
  )
}
