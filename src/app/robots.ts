import type { MetadataRoute } from 'next'
import { siteUrl } from '@/lib/site'

/** Only the public directory is indexable; the admin area and the API are not. */
export default function robots(): MetadataRoute.Robots {
  return {
    rules: [{ userAgent: '*', allow: '/', disallow: ['/admin', '/api/', '/search'] }],
    sitemap: `${siteUrl()}/sitemap.xml`,
  }
}
