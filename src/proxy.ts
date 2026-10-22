import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

/**
 * Public directory: every page is open. Administration (/admin/*): visitors without a session cookie are sent to the
 * admin sign-in page. This is only a navigation convenience — the backend authorizes every admin API call itself.
 */
/** Old numeric system URLs (and merged ids) → the canonical slug URL, as a real 308 before any rendering starts. */
async function legacySystemRedirect(request: NextRequest): Promise<NextResponse | null> {
  const m = request.nextUrl.pathname.match(/^\/systems\/(\d{1,9})(\/.*)?$/)
  if (!m) return null
  const base = (process.env.API_INTERNAL_URL || process.env.BACKEND_URL || request.nextUrl.origin).replace(/\/$/, '')
  try {
    const res = await fetch(`${base}/api/v1/design-systems/${m[1]}`, { headers: { Accept: 'application/json' } })
    if (!res.ok) return null
    const slug = (await res.json())?.data?.slug
    if (typeof slug !== 'string' || !/^[a-z0-9-]+$/.test(slug)) return null
    const url = request.nextUrl.clone()
    url.pathname = `/systems/${slug}${m[2] ?? ''}`
    return NextResponse.redirect(url, 308)
  } catch {
    return null // the page itself still resolves the id
  }
}

export async function proxy(request: NextRequest) {
  const legacy = await legacySystemRedirect(request)
  if (legacy) return withHeaders(legacy, false)
  const { pathname } = request.nextUrl
  const isAdmin = pathname === '/admin' || pathname.startsWith('/admin/')
  if (isAdmin && pathname !== '/admin/login' && !request.cookies.get('dsrp_session')?.value) {
    const loginUrl = new URL('/admin/login', request.url)
    if (pathname !== '/admin') loginUrl.searchParams.set('next', pathname)
    return withHeaders(NextResponse.redirect(loginUrl), true)
  }
  return withHeaders(NextResponse.next(), isAdmin, pathname === '/playground-frame')
}

function withHeaders(response: NextResponse, isAdmin: boolean, frameable = false) {
  // only the component preview may be framed, and only by this site (the playground page)
  response.headers.set('X-Frame-Options', frameable ? 'SAMEORIGIN' : 'DENY')
  if (frameable) response.headers.set('Content-Security-Policy', "frame-ancestors 'self'")
  response.headers.set('X-Content-Type-Options', 'nosniff')
  response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin')
  if (isAdmin) response.headers.set('X-Robots-Tag', 'noindex, nofollow, noarchive')
  return response
}

export const config = {
  // pages only: API calls go straight to the backend service, static assets need no headers here
  matcher: ['/((?!api/|_next/static|_next/image|favicon.ico).*)'],
}
