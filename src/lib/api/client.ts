/**
 * Single transport for every backend call. Same-origin `/api/v1` (proxied by Next), cookie session,
 * CSRF double-submit header on unsafe methods, typed errors, AbortSignal support.
 */
import type { ErrorBody } from './types'

export const API_BASE = '/api/v1'

export class ApiError extends Error {
  status: number
  code: string
  details: ErrorBody['details']
  requestId?: string | null

  constructor(status: number, body: Partial<ErrorBody> | undefined, fallback: string) {
    super(body?.message || fallback)
    this.name = 'ApiError'
    this.status = status
    this.code = body?.code || (status === 0 ? 'NETWORK_ERROR' : 'HTTP_ERROR')
    this.details = body?.details || []
    this.requestId = body?.request_id
  }
}

export type QueryValue = string | number | boolean | null | undefined | (string | number)[]
export type Query = Record<string, QueryValue>

export function toQueryString(query?: Query): string {
  if (!query) return ''
  const p = new URLSearchParams()
  for (const [k, v] of Object.entries(query)) {
    if (v === undefined || v === null || v === '') continue
    if (Array.isArray(v)) v.forEach((x) => p.append(k, String(x)))
    else p.set(k, String(v))
  }
  const s = p.toString()
  return s ? `?${s}` : ''
}

function csrfToken(): string | undefined {
  if (typeof document === 'undefined') return undefined
  const m = document.cookie.match(/(?:^|;\s*)dsrp_csrf=([^;]+)/)
  return m ? decodeURIComponent(m[1]) : undefined
}

interface Options {
  method?: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE'
  query?: Query
  body?: unknown
  signal?: AbortSignal
}

export async function api<T>(path: string, { method = 'GET', query, body, signal }: Options = {}): Promise<T> {
  const headers: Record<string, string> = { Accept: 'application/json' }
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (method !== 'GET') {
    const t = csrfToken()
    if (t) headers['X-CSRF-Token'] = t
  }
  let res: Response
  try {
    res = await fetch(`${API_BASE}${path}${toQueryString(query)}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      credentials: 'same-origin',
      signal,
      cache: 'no-store',
    })
  } catch (e) {
    if ((e as Error).name === 'AbortError') throw e
    throw new ApiError(0, undefined, 'Could not reach the API. Check your connection or the backend status.')
  }
  if (res.status === 204) return undefined as T
  let json: unknown
  try {
    json = await res.json()
  } catch {
    json = undefined
  }
  if (!res.ok) {
    const err = (json as { error?: ErrorBody } | undefined)?.error
    throw new ApiError(res.status, err, `Request failed (${res.status})`)
  }
  return json as T
}
