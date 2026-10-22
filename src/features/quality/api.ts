'use client'

import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api/client'
import { qk } from '@/lib/api/keys'
import type { IntakeCheckOut, IntakeOut, IntakeRequest, Item, Page } from '@/lib/api/types'

export type IssueKind =
  | 'duplicate_candidates' | 'missing_official_url' | 'invalid_links' | 'unverified_github' | 'figma_not_found'
  | 'figma_unchecked' | 'orphaned_records' | 'extraction_failures' | 'needs_recrawl'

export interface QualitySummary {
  counts: Record<IssueKind, number>
  labels: Record<IssueKind, string>
  orphans: Record<string, number>
  failed_jobs_30d: number
  storybook_not_extracted: number
  systems_total: number
  figma_verified_systems: number
}
export interface QualityIssue { kind: string; id: number | string; title: string; subtitle: string | null; detail: string | null; href: string | null }

export const useQuality = () =>
  useQuery({ queryKey: qk.quality('summary'), queryFn: ({ signal }) => api<Item<QualitySummary>>('/quality', { signal }).then((r) => r.data) })
export const useQualityIssues = (kind: IssueKind | null, page: number) =>
  useQuery({
    queryKey: qk.quality('issues', { kind, page }),
    queryFn: ({ signal }) => api<Page<QualityIssue>>('/quality/issues', { query: { kind: kind!, page, page_size: 25 }, signal }),
    enabled: !!kind,
    placeholderData: keepPreviousData,
  })

export function useIntakeCheck() {
  return useMutation({ mutationFn: (body: { url: string; name?: string }) => api<Item<IntakeCheckOut>>('/intake/check', { method: 'POST', body }).then((r) => r.data) })
}
export function useIntake() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: IntakeRequest) => api<Item<IntakeOut>>('/intake', { method: 'POST', body }).then((r) => r.data),
    onSuccess: () => ['systems', 'system', 'quality', 'dashboard', 'jobs'].forEach((k) => qc.invalidateQueries({ queryKey: [k] })),
  })
}
