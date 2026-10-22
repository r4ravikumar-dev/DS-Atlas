import type { Prop } from '@/lib/api/types'

/** Props whose documented values usually describe visual variants, sizes or states. */
const AXIS = /^(variant|size|color|colou?rScheme|appearance|state|kind|tone|intent|status|shape|density|orientation|emphasis|type|placement|radius|weight)$/i

/**
 * Variant axes read straight from the documented API: a prop counts only when its declared type is a union of
 * string literals (e.g. `"primary" | "secondary"`). Nothing is inferred from names alone.
 */
export function variantAxes(props: Prop[]) {
  const out: { name: string; part: string | null; values: string[]; default: string | null }[] = []
  const seen = new Set<string>()
  for (const p of props) {
    if (!AXIS.test(p.name) || !p.type || seen.has(p.name)) continue
    const members = p.type.split('|').map((x) => x.trim()).filter((x) => x && x !== 'undefined' && x !== 'null')
    const literals = members.map((m) => m.match(/^(['"])(.{1,40})\1$/)?.[2])
    if (members.length < 2 || literals.some((l) => l === undefined)) continue
    seen.add(p.name)
    out.push({ name: p.name, part: p.subcomponent, values: literals as string[], default: p.default_value?.replace(/^['"]|['"]$/g, '') ?? null })
  }
  return out
}

/** A TypeScript props signature generated from the documented API (labelled as generated, never presented as source). */
export function propsSignature(component: string, props: Prop[], max = 24) {
  const own = props.filter((p) => !p.subcomponent || p.subcomponent === component).slice(0, max)
  if (own.length === 0) return null
  const id = (n: string) => (/^[A-Za-z_$][\w$]*$/.test(n) ? n : JSON.stringify(n))
  const req = (p: Prop) => !!p.required && !/^(false|no)$/i.test(p.required)
  const lines = own.map((p) => `  ${id(p.name)}${req(p) ? '' : '?'}: ${(p.type ?? 'unknown').replace(/\s+/g, ' ').slice(0, 140)}`)
  const more = props.filter((p) => !p.subcomponent || p.subcomponent === component).length - own.length
  return `interface ${component.replace(/[^\w]/g, '') || 'Component'}Props {\n${lines.join('\n')}${more > 0 ? `\n  // …${more} more documented props` : ''}\n}`
}
