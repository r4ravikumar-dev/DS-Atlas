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
      console.warn('[next.config] BACKEND_URL is not set — /api/v1 requests will 404. Configure it per environment.')
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
          { key: 'X-Robots-Tag', value: 'noindex, nofollow, noarchive' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
        ],
      },
    ]
  },
}

export default nextConfig
