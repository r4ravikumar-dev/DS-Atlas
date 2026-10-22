import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

// Public paths that do not require an active session
const PUBLIC_PATHS = [
  '/platform/login',
  '/platform/invite',
  '/favicon.ico',
]

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl
  const sessionCookie = request.cookies.get('dsrp_session')
  const hasSession = Boolean(sessionCookie?.value)

  // Skip static assets and internal Next.js requests
  if (
    pathname.startsWith('/_next') ||
    pathname.startsWith('/api/') || // the backend authorizes every API call itself and returns JSON 401/403
    pathname.includes('.')
  ) {
    const response = NextResponse.next()
    applySecurityHeaders(response)
    return response
  }

  const isPublic = PUBLIC_PATHS.some(
    (p) => pathname === p || pathname.startsWith(`${p}/`)
  )

  // If unauthenticated and trying to access any protected page (including / and /platform/*)
  if (!hasSession && !isPublic) {
    const loginUrl = new URL('/platform/login', request.url)
    if (pathname !== '/' && pathname !== '/platform') {
      loginUrl.searchParams.set('next', pathname)
    }
    const response = NextResponse.redirect(loginUrl)
    applySecurityHeaders(response)
    return response
  }

  // If authenticated and visiting login, redirect to dashboard
  if (hasSession && pathname === '/platform/login') {
    const dashUrl = new URL('/platform', request.url)
    const response = NextResponse.redirect(dashUrl)
    applySecurityHeaders(response)
    return response
  }

  const response = NextResponse.next()
  applySecurityHeaders(response)
  return response
}

function applySecurityHeaders(response: NextResponse) {
  response.headers.set('X-Frame-Options', 'DENY')
  response.headers.set('X-Content-Type-Options', 'nosniff')
  response.headers.set('X-Robots-Tag', 'noindex, nofollow, noarchive')
  response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin')
}

export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     */
    '/((?!_next/static|_next/image).*)',
  ],
}
