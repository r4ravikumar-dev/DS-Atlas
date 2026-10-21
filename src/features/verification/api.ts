'use client'

import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, type Query } from '@/lib/api/client'
import { qk } from '@/lib/api/keys'
import type { AttributeEvidence, Item, Page } from '@/lib/api/types'

export function usePriorityVerification(limit: number = 15) {
  return useQuery({
    queryKey: qk.verification('priority', limit),
    queryFn: ({ signal }) =>
      api<Item<Array<Record<string, unknown>>>>('/verification/priority', { query: { limit }, signal }).then(
        (r) => r.data,
      ),
  })
}

export function useAttributeEvidence(q?: Query) {
  return useQuery({
    queryKey: qk.verification('attributes', q),
    queryFn: ({ signal }) => api<Page<AttributeEvidence>>('/verification/attributes', { query: q, signal }),
    placeholderData: keepPreviousData,
  })
}

export function useStartOfficialVerification() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ limit = 15, max_pages = 45 }: { limit?: number; max_pages?: number }) =>
      api<Item<{ job_ids: string[]; sources: Array<Record<string, unknown>> }>>('/verification/official-docs', {
        method: 'POST',
        query: { limit, max_pages },
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['sources'] })
      qc.invalidateQueries({ queryKey: ['jobs'] })
      qc.invalidateQueries({ queryKey: ['verification'] })
    },
  })
}
