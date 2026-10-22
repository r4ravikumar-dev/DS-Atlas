import { timingSafeEqual } from 'node:crypto'
import { revalidateTag } from 'next/cache'
import { NextResponse, type NextRequest } from 'next/server'

const ALLOWED = /^(public|stats|systems|components|tokens|guidelines|search|(system|component|token):\d{1,9})$/

function authorized(req: NextRequest) {
  const secret = process.env.REVALIDATE_SECRET
  if (!secret) return false
  const got = Buffer.from(req.headers.get('authorization') ?? '')
  const want = Buffer.from(`Bearer ${secret}`)
  return got.length === want.length && timingSafeEqual(got, want)
}

/**
 * Called by the backend after a daily sync that changed public content (never when nothing changed), with the cache
 * tags to refresh — e.g. ["stats", "systems", "system:12"]. Disabled (404) unless REVALIDATE_SECRET is configured.
 */
export async function POST(req: NextRequest) {
  if (!process.env.REVALIDATE_SECRET) return new NextResponse(null, { status: 404 })
  if (!authorized(req)) return NextResponse.json({ error: { code: 'UNAUTHORIZED', message: 'Invalid revalidation secret.' } }, { status: 401 })
  let tags: unknown
  try {
    tags = (await req.json())?.tags
  } catch {
    return NextResponse.json({ error: { code: 'VALIDATION_ERROR', message: 'Body must be JSON: {"tags": [...]}' } }, { status: 422 })
  }
  if (!Array.isArray(tags) || tags.length === 0 || tags.length > 200 || !tags.every((t) => typeof t === 'string' && ALLOWED.test(t))) {
    return NextResponse.json({ error: { code: 'VALIDATION_ERROR', message: 'tags must be 1–200 known cache tags.' } }, { status: 422 })
  }
  for (const t of new Set(tags as string[])) revalidateTag(t, 'max')
  return NextResponse.json({ data: { revalidated: [...new Set(tags)] } })
}
