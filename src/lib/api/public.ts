import 'server-only'
import { getItem } from './server'

/** Shape of GET /stats — backend-computed counts and freshness of the published dataset. */
export interface PublicStats {
  design_systems: number; components: number; tokens: number; guidelines: number; patterns: number
  storybook_projects: number; stories: number; variants: number; systems_with_github: number; systems_with_figma: number
  /** sources that contributed records (added with the public directory; optional for older backends) */
  sources_indexed?: number
  content_updated_at: string | null; last_sync_at: string | null
}

export const getStats = () => getItem<PublicStats>('/stats', { tags: ['stats'] })

export const fmtDate = (d?: string | null) => (d ? new Date(d).toLocaleDateString('en', { year: 'numeric', month: 'short', day: 'numeric', timeZone: 'UTC' }) : null)
