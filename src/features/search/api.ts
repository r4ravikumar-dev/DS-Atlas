'use client'

import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { api, type Query } from '@/lib/api/client'
import { qk } from '@/lib/api/keys'
import type { Page, SearchHit } from '@/lib/api/types'

export const useSearch = (q: Query) =>
  useQuery({
    queryKey: qk.search(q),
    queryFn: ({ signal }) => api<Page<SearchHit>>('/search', { query: q, signal }),
    enabled: typeof q.q === 'string' && q.q.trim().length > 0,
    placeholderData: keepPreviousData,
  })
