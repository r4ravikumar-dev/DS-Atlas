import type { NextConfig } from 'next'
import path from 'node:path'

/**
 * The browser only ever talks to the same origin. `/api/v1/*` is proxied to the backend whose base URL
 * comes from the server-only BACKEND_URL environment variable (never exposed to client bundles).
 */
const backend = process.env.BACKEND_URL

const nextConfig: NextConfig = {
  sassOptions: {
    loadPaths: [path.join(process.cwd(), 'src/styles')],
  },
  async rewrites() {
    if (!backend) {
      // On Vercel (services mode) the top-level rewrite in vercel.json routes /api/* to the backend service before Next.js runs.
      if (!process.env.VERCEL) console.warn('[next.config] BACKEND_URL is not set — /api/v1 requests will 404. Configure it per environment.')
      return []
    }
    return [{ source: '/api/v1/:path*', destination: `${backend.replace(/\/$/, '')}/api/v1/:path*` }]
  },
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
        ],
      },
      // the component preview may only be framed by this site's own playground pages
      { source: '/playground-frame', headers: [{ key: 'X-Frame-Options', value: 'SAMEORIGIN' }, { key: 'Content-Security-Policy', value: "frame-ancestors 'self'" }, { key: 'X-Robots-Tag', value: 'noindex, nofollow' }] },
      // the public directory is indexable; the admin area is not
      { source: '/admin/:path*', headers: [{ key: 'X-Robots-Tag', value: 'noindex, nofollow, noarchive' }] },
      { source: '/admin', headers: [{ key: 'X-Robots-Tag', value: 'noindex, nofollow, noarchive' }] },
    ]
  },
}

export default nextConfig
