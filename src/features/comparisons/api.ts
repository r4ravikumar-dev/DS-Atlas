'use client'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api/client'
import { qk } from '@/lib/api/keys'
import type { Comparison, ComparisonCreate, Item, Page } from '@/lib/api/types'

export const useComparisons = () =>
  useQuery({ queryKey: qk.comparisons(), queryFn: ({ signal }) => api<Page<Comparison>>('/comparisons', { query: { page_size: 50 }, signal }) })
export const useComparison = (id: string) =>
  useQuery({ queryKey: qk.comparison(id), queryFn: ({ signal }) => api<Item<Comparison>>(`/comparisons/${id}`, { signal }).then((r) => r.data) })

export function useCreateComparison() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: ComparisonCreate) => api<Item<Comparison>>('/comparisons', { method: 'POST', body }),
    onSuccess: (r) => (qc.setQueryData(qk.comparison(r.data.id), r.data), qc.invalidateQueries({ queryKey: ['comparisons'] })),
  })
}
export function useRegenerate(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api<Item<Comparison>>(`/comparisons/${id}/generate`, { method: 'POST' }),
    onSuccess: (r) => qc.setQueryData(qk.comparison(id), r.data),
  })
}
export function useDeleteComparison() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api<void>(`/comparisons/${id}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['comparisons'] }),
  })
}
