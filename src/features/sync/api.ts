'use client'

import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api/client'
import type { Item, Page } from '@/lib/api/types'

export interface SyncSource {
  source_id: number; key: string; name: string; job_ids: string[]; outcome: string; reason?: string; error?: string | null; partial?: boolean
  attempts?: number; records_seen?: number | null; records_created?: number; records_updated?: number; records_unchanged?: number
  records_marked_stale?: number; stale_suppressed?: number; records_preserved?: number | null; content_changed?: boolean
}
export interface SyncRun {
  id: string; trigger: string; status: string; scheduled_for: string | null; started_at: string; finished_at: string | null
  attempt: number; built: boolean; metrics: Record<string, unknown>; sources: SyncSource[] | null; errors: { source: string; error: string }[]; next_run_at: string | null
}
export interface SyncStatus {
  enabled: boolean; interval_hours: number; hour_utc: number; minute_utc: number; timezone: string; next_run_at: string | null
  last_heartbeat_at: string | null; scheduler_alive: boolean; current_run: SyncRun | null; last_run: SyncRun | null; last_successful_run_at: string | null
}
export interface RecordChangeRow { id: number; sync_run_id: string | null; source_id: number | null; record_key: string; record_type: string; change: string; title: string | null; at: string }

export const useSyncStatus = () =>
  useQuery({ queryKey: ['sync', 'status'], queryFn: ({ signal }) => api<Item<SyncStatus>>('/admin/sync', { signal }).then((r) => r.data),
    refetchInterval: (q) => (q.state.data?.current_run ? 5_000 : 30_000) })
export const useSyncRuns = (page: number) =>
  useQuery({ queryKey: ['sync', 'runs', page], queryFn: ({ signal }) => api<Page<SyncRun>>('/admin/sync/runs', { query: { page, page_size: 15 }, signal }), placeholderData: keepPreviousData })
export const useSyncRun = (id: string | null) =>
  useQuery({ queryKey: ['sync', 'run', id], queryFn: ({ signal }) => api<Item<SyncRun>>(`/admin/sync/runs/${id}`, { signal }).then((r) => r.data), enabled: !!id })
export const useChanges = (q: { sync_run_id?: string | null; change?: string | null; page: number }) =>
  useQuery({ queryKey: ['sync', 'changes', q], queryFn: ({ signal }) => api<Page<RecordChangeRow>>('/admin/changes', { query: { ...q, page_size: 25 }, signal }), placeholderData: keepPreviousData })

function useInvalidate() {
  const qc = useQueryClient()
  return () => ['sync', 'dashboard', 'jobs'].forEach((k) => qc.invalidateQueries({ queryKey: [k] }))
}
export function useRunNow() {
  const done = useInvalidate()
  return useMutation({ mutationFn: () => api<Item<SyncRun>>('/admin/sync/run', { method: 'POST' }), onSuccess: done })
}
export function useUpdateSchedule() {
  const done = useInvalidate()
  return useMutation({ mutationFn: (body: { enabled?: boolean; hour_utc?: number; minute_utc?: number }) => api<Item<SyncStatus>>('/admin/sync/schedule', { method: 'PATCH', body }), onSuccess: done })
}
