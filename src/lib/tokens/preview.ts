/**
 * Decide whether a collected token value can be previewed, and how. Values are never transformed or guessed:
 * a preview is only produced when the stored value is itself valid CSS of the expected kind (unitless numbers
 * such as `4` are shown as text, not assumed to be pixels). The strict patterns also keep arbitrary strings
 * out of inline styles.
 */
export type PreviewKind = 'color' | 'dimension' | 'radius' | 'spacing' | 'font-size' | 'font-family' | 'font-weight' | 'shadow' | 'duration' | 'easing' | 'none'

export interface TokenLike {
  path: string
  name?: string | null
  type?: string | null
  raw_value?: string | null
  resolved_value?: string | null
}

const HEX = /^#(?:[0-9a-f]{3,4}|[0-9a-f]{6}|[0-9a-f]{8})$/i
const NUM = String.raw`-?(?:\d+\.?\d*|\.\d+)`
const FN_COLOR = new RegExp(String.raw`^(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch)\(\s*(?:${NUM}(?:%|deg)?\s*[,/ ]?\s*){2,4}\)$`, 'i')
const DIMENSION = new RegExp(String.raw`^${NUM}(?:px|rem|em)$`)
const DURATION = new RegExp(String.raw`^${NUM}m?s$`)
const EASING = new RegExp(String.raw`^(?:ease|ease-in|ease-out|ease-in-out|linear|cubic-bezier\(\s*${NUM}\s*,\s*${NUM}\s*,\s*${NUM}\s*,\s*${NUM}\s*\))$`)
const WEIGHT = /^(?:[1-9]00|normal|bold)$/
const FAMILY = /^[\w\s"',.-]{1,160}$/
const SHADOW_PART = new RegExp(String.raw`^(?:inset\s+)?(?:${NUM}(?:px|rem|em)?\s+){2,3}${NUM}(?:px|rem|em)?\s+(?:#[0-9a-f]{3,8}|(?:rgba?|hsla?)\([\d\s.,%/]+\))$`, 'i')

export const tokenValue = (t: TokenLike) => (t.resolved_value ?? t.raw_value ?? '').trim()

export const isColor = (v: string) => HEX.test(v) || FN_COLOR.test(v)
export const isShadow = (v: string) => v.length < 300 && v.split(/,(?![^(]*\))/).every((p) => SHADOW_PART.test(p.trim()))

/** Lowercased "where does this token live" hint: path, name and declared type. */
const hint = (t: TokenLike) => `${t.path} ${t.name ?? ''} ${t.type ?? ''}`.toLowerCase()

export function previewKind(t: TokenLike): PreviewKind {
  const v = tokenValue(t)
  if (!v) return 'none'
  const h = hint(t)
  if (isColor(v)) return 'color'
  if (DURATION.test(v) && /duration|motion|transition|anim|delay/.test(h)) return 'duration'
  if (EASING.test(v) && /eas|motion|curve|transition/.test(h)) return 'easing'
  if (isShadow(v) && /shadow|elevation/.test(h)) return 'shadow'
  if (WEIGHT.test(v) && /weight/.test(h)) return 'font-weight'
  if (/font-?family|fontfamily|typeface/.test(h) && FAMILY.test(v) && !DIMENSION.test(v)) return 'font-family'
  if (DIMENSION.test(v)) {
    if (/radius|rounded|corner/.test(h)) return 'radius'
    if (/font-?size|fontsize|text-size|type-?scale|\bh[1-6]\b/.test(h)) return 'font-size'
    if (/space|spacing|gap|padding|margin|inset|gutter|size/.test(h)) return 'spacing'
    return 'dimension'
  }
  return 'none'
}

/** Foundations groups shown on a system page, in display order. */
export const FOUNDATION_GROUPS: { kind: PreviewKind; label: string }[] = [
  { kind: 'color', label: 'Colour' },
  { kind: 'font-family', label: 'Typefaces' },
  { kind: 'font-size', label: 'Type scale' },
  { kind: 'font-weight', label: 'Font weights' },
  { kind: 'spacing', label: 'Spacing' },
  { kind: 'radius', label: 'Radius' },
  { kind: 'shadow', label: 'Elevation' },
  { kind: 'duration', label: 'Motion — durations' },
  { kind: 'easing', label: 'Motion — easing' },
]

/** Pixel size of a dimension for proportional diagrams (rem/em at the 16px default). */
export function toPx(v: string): number | null {
  const m = v.match(new RegExp(String.raw`^(${NUM})(px|rem|em)$`))
  if (!m) return null
  const n = Number(m[1])
  return m[2] === 'px' ? n : n * 16
}

export function toMs(v: string): number | null {
  const m = v.match(new RegExp(String.raw`^(${NUM})(ms|s)$`))
  if (!m) return null
  return m[2] === 's' ? Number(m[1]) * 1000 : Number(m[1])
}

/** Group tokens by preview kind; unpreviewable tokens are dropped (they're still listed in the token table). */
export function groupFoundations<T extends TokenLike>(tokens: T[]) {
  const out = new Map<PreviewKind, T[]>()
  for (const t of tokens) {
    const k = previewKind(t)
    if (k === 'none' || k === 'dimension') continue
    out.set(k, [...(out.get(k) ?? []), t])
  }
  return FOUNDATION_GROUPS.filter((g) => out.get(g.kind)?.length).map((g) => ({ ...g, tokens: out.get(g.kind)! }))
}
