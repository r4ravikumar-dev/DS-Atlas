import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

/**
 * Public directory: every page is open. Administration (/admin/*): visitors without a session cookie are sent to the
 * admin sign-in page. This is only a navigation convenience — the backend authorizes every admin API call itself.
 */
export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl
  const isAdmin = pathname === '/admin' || pathname.startsWith('/admin/')
  if (isAdmin && pathname !== '/admin/login' && !request.cookies.get('dsrp_session')?.value) {
    const loginUrl = new URL('/admin/login', request.url)
    if (pathname !== '/admin') loginUrl.searchParams.set('next', pathname)
    return withHeaders(NextResponse.redirect(loginUrl), true)
  }
  return withHeaders(NextResponse.next(), isAdmin)
}

function withHeaders(response: NextResponse, isAdmin: boolean) {
  response.headers.set('X-Frame-Options', 'DENY')
  response.headers.set('X-Content-Type-Options', 'nosniff')
  response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin')
  if (isAdmin) response.headers.set('X-Robots-Tag', 'noindex, nofollow, noarchive')
  return response
}

export const config = {
  // pages only: API calls go straight to the backend service, static assets need no headers here
  matcher: ['/((?!api/|_next/static|_next/image|favicon.ico).*)'],
}
