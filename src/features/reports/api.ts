'use client'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api/client'
import { qk } from '@/lib/api/keys'
import type { ExportCreate, ExportJob, Item, JobAccepted, Page, Report, ReportDetail } from '@/lib/api/types'

export const useReports = () =>
  useQuery({ queryKey: qk.reports(), queryFn: ({ signal }) => api<Page<Report>>('/reports', { query: { page_size: 20 }, signal }) })
export const useReport = (id: string | null) =>
  useQuery({ queryKey: qk.report(id ?? ''), queryFn: ({ signal }) => api<Item<ReportDetail>>(`/reports/${id}`, { signal }).then((r) => r.data), enabled: !!id })
export const useExports = (enabled: boolean) =>
  useQuery({
    queryKey: qk.exports(),
    queryFn: ({ signal }) => api<Page<ExportJob>>('/export-jobs', { query: { page_size: 15 }, signal }),
    enabled,
    refetchInterval: (q) => (q.state.data?.data.some((j) => j.status === 'queued' || j.status === 'running') ? 2000 : false),
  })
export function useCreateExport() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: ExportCreate) => api<Item<JobAccepted>>('/export-jobs', { method: 'POST', body }),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.exports() }),
  })
}
