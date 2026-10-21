'use client'

import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, type Query } from '@/lib/api/client'
import { qk } from '@/lib/api/keys'
import type { Item, Job, JobAccepted, JobEvent, Page } from '@/lib/api/types'

const ACTIVE = new Set(['queued', 'running'])
export const isActive = (j?: Job) => !!j && ACTIVE.has(j.status)

export const useJobs = (q: Query) =>
  useQuery({
    queryKey: qk.jobs(q),
    queryFn: ({ signal }) => api<Page<Job>>('/crawl-jobs', { query: q, signal }),
    placeholderData: keepPreviousData,
    refetchInterval: (query) => (query.state.data?.data.some(isActive) ? 3000 : false),
  })

/** Polls while the job is active; on reaching a terminal state, refreshes everything the job could have changed. */
export function useJob(id: string) {
  const qc = useQueryClient()
  return useQuery({
    queryKey: qk.job(id),
    queryFn: async ({ signal }) => {
      const prev = qc.getQueryData<Job>(qk.job(id))
      const j = (await api<Item<Job>>(`/crawl-jobs/${id}`, { signal })).data
      if (prev && isActive(prev) && !isActive(j)) {
        for (const k of ['dashboard', 'sources', 'source', 'systems', 'components', 'tokens', 'guidelines', 'reports', 'facets']) qc.invalidateQueries({ queryKey: [k] })
      }
      return j
    },
    refetchInterval: (query) => (isActive(query.state.data) ? 2000 : false),
  })
}

export const useJobEvents = (id: string, active: boolean) =>
  useQuery({
    queryKey: qk.jobEvents(id),
    queryFn: ({ signal }) => api<Page<JobEvent>>(`/crawl-jobs/${id}/events`, { query: { page_size: 100 }, signal }),
    refetchInterval: active ? 2000 : false,
  })

export function useCancelJob() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api<Item<Job>>(`/crawl-jobs/${id}/cancel`, { method: 'POST' }),
    onSuccess: (r) => {
      qc.setQueryData(qk.job(r.data.id), r.data)
      qc.invalidateQueries({ queryKey: ['jobs'] })
    },
  })
}

export function useRetryJob() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api<Item<JobAccepted>>(`/crawl-jobs/${id}/retry`, { method: 'POST' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['jobs'] }),
  })
}

export function useCrawlAll() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { source_ids?: number[]; rebuild: boolean }) => api<Item<JobAccepted>>('/crawl-jobs', { method: 'POST', body }),
    onSuccess: () => (qc.invalidateQueries({ queryKey: ['jobs'] }), qc.invalidateQueries({ queryKey: ['dashboard'] })),
  })
}

export function useRebuild() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api<Item<JobAccepted>>('/crawl-jobs/build', { method: 'POST' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['jobs'] }),
  })
}
