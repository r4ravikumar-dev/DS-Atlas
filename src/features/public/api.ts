'use client'

import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api/client'
import type { Item } from '@/lib/api/types'

export interface PublicStats {
  design_systems: number; components: number; tokens: number; guidelines: number; patterns: number
  storybook_projects: number; stories: number; variants: number; systems_with_github: number; systems_with_figma: number
  content_updated_at: string | null; last_sync_at: string | null
}
export interface CompareResult { kind: 'systems' | 'components'; dimensions: string[]; result: Record<string, unknown> }

export const useStats = () =>
  useQuery({ queryKey: ['public', 'stats'], queryFn: ({ signal }) => api<Item<PublicStats>>('/stats', { signal }).then((r) => r.data), staleTime: 300_000 })

export const usePublicCompare = (kind: 'systems' | 'components', ids: number[], dimensions: string[]) =>
  useQuery({
    queryKey: ['public', 'compare', kind, ids, dimensions],
    queryFn: ({ signal }) => api<Item<CompareResult>>('/compare', { query: { kind, ids: ids.join(','), dimensions: dimensions.join(',') }, signal }).then((r) => r.data),
    enabled: ids.length >= 2,
  })
