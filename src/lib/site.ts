/** Public site identity and absolute URL (canonical links, sitemap, Open Graph). */
export const SITE_NAME = 'Design Systems Directory'
export const SITE_DESCRIPTION =
  'Explore design systems, components, variants, design tokens, guidelines and Storybook stories in one searchable place — collected from official sources, with provenance on every record.'

export function siteUrl(): string {
  const explicit = process.env.NEXT_PUBLIC_SITE_URL
  if (explicit) return explicit.replace(/\/$/, '')
  const vercel = process.env.VERCEL_PROJECT_PRODUCTION_URL || process.env.VERCEL_URL
  if (vercel) return `https://${vercel}`
  return 'http://localhost:3000'
}
