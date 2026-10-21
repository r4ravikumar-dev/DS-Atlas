'use client'

import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api/client'
import { qk } from '@/lib/api/keys'
import type { DashboardSummary, Item, Job } from '@/lib/api/types'

export interface CoverageRow { id: number; key: string; name: string; status: string; pages_attempted: number; pages_ok: number; error_count: number; last_success_at: string | null; records: number; urls: number }
export interface CategoryRow { category: string; name: string; total: number; by_type: Record<string, number> }
export interface Activity { jobs: Job[]; recent_records: { id: number; record_type: string; title: string; updated_at: string; source_key: string }[]; jobs_per_day: { date: string; status: string; count: number }[] }

export const useSummary = () =>
  useQuery({ queryKey: qk.dashboard('summary'), queryFn: ({ signal }) => api<Item<DashboardSummary>>('/dashboard/summary', { signal }).then((r) => r.data), refetchInterval: 15_000 })
export const useCoverage = () =>
  useQuery({ queryKey: qk.dashboard('coverage'), queryFn: ({ signal }) => api<Item<CoverageRow[]>>('/dashboard/source-coverage', { signal }).then((r) => r.data) })
export const useCategories = () =>
  useQuery({ queryKey: qk.dashboard('categories'), queryFn: ({ signal }) => api<Item<CategoryRow[]>>('/dashboard/category-distribution', { signal }).then((r) => r.data) })
export const useActivity = (days = 30) =>
  useQuery({ queryKey: qk.dashboard('activity', days), queryFn: ({ signal }) => api<Item<Activity>>('/dashboard/activity', { query: { days, limit: 12 }, signal }).then((r) => r.data), refetchInterval: 10_000 })
