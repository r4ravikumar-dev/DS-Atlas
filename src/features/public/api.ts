'use client'

import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api/client'
import type { Item } from '@/lib/api/types'

export interface CompareResult { kind: 'systems' | 'components'; dimensions: string[]; result: Record<string, unknown> }

export const usePublicCompare = (kind: 'systems' | 'components', ids: number[], dimensions: string[]) =>
  useQuery({
    queryKey: ['public', 'compare', kind, ids, dimensions],
    queryFn: ({ signal }) => api<Item<CompareResult>>('/compare', { query: { kind, ids: ids.join(','), dimensions: dimensions.join(',') }, signal }).then((r) => r.data),
    enabled: ids.length >= 2,
  })
