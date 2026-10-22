import 'server-only'
import { toQueryString, type Query } from './client'
import type { Item, Page } from './types'

/**
 * Server-side reads of the public API for Server Components, metadata and the sitemap.
 *
 * Calls go straight to the backend (no extra hop through this app's own /api proxy). The base URL is server-only:
 *   1. API_INTERNAL_URL or BACKEND_URL when configured (local development, self-hosting);
 *   2. on Vercel production, the project's production domain — the backend service answers /api/* there, and it is
 *      already live while a new deployment builds, so prerendered pages get real data;
 *   3. on other Vercel deployments, the deployment's own URL (Deployment Protection is passed with
 *      VERCEL_AUTOMATION_BYPASS_SECRET when that is set).
 * Responses go into Next's data cache with tags so a content change can revalidate just the affected data
 * (see src/app/revalidate/route.ts).
 */
function base(): string {
  const explicit = process.env.API_INTERNAL_URL || process.env.BACKEND_URL
  if (explicit) return explicit.replace(/\/$/, '')
  const prod = process.env.VERCEL_ENV === 'production' ? process.env.VERCEL_PROJECT_PRODUCTION_URL : undefined
  const host = prod || process.env.VERCEL_URL
  if (host) return `https://${host}`
  return 'http://localhost:8000'
}

function headers(): Record<string, string> {
  const h: Record<string, string> = { Accept: 'application/json' }
  // identifies server-side rendering to the backend so shared egress IPs aren't rate-limited as one anonymous client
  if (process.env.RENDER_API_KEY) h['x-render-key'] = process.env.RENDER_API_KEY
  const bypass = process.env.VERCEL_AUTOMATION_BYPASS_SECRET
  if (bypass && !process.env.API_INTERNAL_URL && !process.env.BACKEND_URL) h['x-vercel-protection-bypass'] = bypass
  return h
}

export class BackendError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = 'BackendError'
  }
}

interface Opts {
  query?: Query
  /** seconds; defaults to 5 minutes — the daily sync is the only writer of public content */
  revalidate?: number
  tags?: string[]
}

export async function backend<T>(path: string, { query, revalidate = 300, tags = [] }: Opts = {}): Promise<T> {
  const url = `${base()}/api/v1${path}${toQueryString(query)}`
  let res: Response
  try {
    res = await fetch(url, { headers: headers(), next: { revalidate, tags: ['public', ...tags] } })
  } catch {
    throw new BackendError(0, 'The directory service is unreachable.')
  }
  if (!res.ok) {
    let message = `Request failed (${res.status}).`
    try {
      const body = await res.json()
      if (body?.error?.message) message = body.error.message
    } catch {}
    throw new BackendError(res.status, message)
  }
  return res.json() as Promise<T>
}

export const getItem = <T>(path: string, opts?: Opts) => backend<Item<T>>(path, opts).then((r) => r.data)
export const getPage = <T>(path: string, opts?: Opts) => backend<Page<T>>(path, opts)

/** Settles to null instead of throwing — for optional sections that must not take the whole page down. */
export async function optional<T>(p: Promise<T>): Promise<T | null> {
  try {
    return await p
  } catch {
    return null
  }
}
