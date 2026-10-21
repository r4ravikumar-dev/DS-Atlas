'use client'

import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, type Query } from '@/lib/api/client'
import { qk } from '@/lib/api/keys'
import type { Coverage, DiscoveredUrl, Item, Job, JobAccepted, Page, Source, SourceCreate, SourceDetail, SourceUpdate } from '@/lib/api/types'

export const useSources = (q: Query) =>
  useQuery({ queryKey: qk.sources(q), queryFn: ({ signal }) => api<Page<Source>>('/sources', { query: q, signal }), placeholderData: keepPreviousData })
export const useSource = (id: number) =>
  useQuery({ queryKey: qk.source(id), queryFn: ({ signal }) => api<Item<SourceDetail>>(`/sources/${id}`, { signal }).then((r) => r.data) })
export const useSourceCoverage = (id: number) =>
  useQuery({ queryKey: qk.sourcePart(id, 'coverage'), queryFn: ({ signal }) => api<Item<Coverage>>(`/sources/${id}/coverage`, { signal }).then((r) => r.data) })
export const useSourceDocuments = (id: number, q: Query) =>
  useQuery({ queryKey: qk.sourcePart(id, 'documents', q), queryFn: ({ signal }) => api<Page<DiscoveredUrl>>(`/sources/${id}/documents`, { query: q, signal }), placeholderData: keepPreviousData })
export const useSourceJobs = (id: number, active: boolean) =>
  useQuery({ queryKey: qk.sourcePart(id, 'jobs'), queryFn: ({ signal }) => api<Page<Job>>(`/sources/${id}/jobs`, { query: { page_size: 10 }, signal }), refetchInterval: active ? 3000 : false })

export function useCreateSource() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: SourceCreate) => api<Item<SourceDetail>>('/sources', { method: 'POST', body }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sources'] }),
  })
}

export function useUpdateSource(id: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: SourceUpdate) => api<Item<SourceDetail>>(`/sources/${id}`, { method: 'PATCH', body }),
    onSuccess: (r) => {
      qc.setQueryData(qk.source(id), r.data)
      qc.invalidateQueries({ queryKey: ['sources'] })
    },
  })
}

export function useStartCrawl(id: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (opts: { rebuild: boolean; refresh: boolean }) => api<Item<JobAccepted>>(`/sources/${id}/crawl`, { method: 'POST', query: opts }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.sourcePart(id, 'jobs') })
      qc.invalidateQueries({ queryKey: ['jobs'] })
      qc.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}
