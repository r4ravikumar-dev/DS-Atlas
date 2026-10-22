import { z } from 'zod'

/** Next.js searchParams as delivered to a page. */
export type RawParams = Record<string, string | string[] | undefined>

const list = (v: string | string[] | undefined) => (v === undefined ? [] : Array.isArray(v) ? v : [v]).map((x) => x.slice(0, 200)).filter(Boolean).slice(0, 20)
const one = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v)?.slice(0, 200) || undefined

const page = z.coerce.number().int().min(1).max(10_000).catch(1)

/**
 * Parse untrusted URL parameters into the backend's query vocabulary. Unknown sort keys fall back to the default;
 * anything malformed is dropped rather than forwarded.
 */
export function parseParams<S extends string>(raw: RawParams, opts: { lists?: string[]; singles?: string[]; flags?: string[]; sorts?: readonly S[] }) {
  const out: Record<string, string | string[] | number | boolean | undefined> = { page: page.parse(one(raw.page) ?? 1) }
  for (const k of opts.lists ?? []) if (raw[k] !== undefined) out[k] = list(raw[k])
  for (const k of opts.singles ?? []) out[k] = one(raw[k])
  for (const k of opts.flags ?? []) if (one(raw[k]) === 'true') out[k] = true
  const sort = one(raw.sort)
  out.sort = sort && (opts.sorts ?? []).includes(sort as S) ? sort : undefined
  out.q = one(raw.q)?.trim() || undefined
  return out
}

/** Rebuild a page URL from the current params, overriding some. */
export function hrefWith(path: string, raw: RawParams, patch: Record<string, string | number | null>) {
  const p = new URLSearchParams()
  for (const [k, v] of Object.entries(raw)) for (const x of list(v)) p.append(k, x)
  for (const [k, v] of Object.entries(patch)) {
    p.delete(k)
    if (v !== null && v !== '' && !(k === 'page' && v === 1)) p.set(k, String(v))
  }
  const qs = p.toString()
  return qs ? `${path}?${qs}` : path
}
