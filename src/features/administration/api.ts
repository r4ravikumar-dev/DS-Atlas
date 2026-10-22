'use client'

import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, type Query } from '@/lib/api/client'
import { qk } from '@/lib/api/keys'
import type { AuditEvent, Config, ConfigUpdate, Item, Page, ReviewItem, User, UserUpdate } from '@/lib/api/types'

export const useUsers = () => useQuery({ queryKey: qk.admin('users'), queryFn: ({ signal }) => api<Page<User>>('/admin/users', { query: { page_size: 100 }, signal }) })
export const useAudit = (page: number) =>
  useQuery({ queryKey: qk.admin('audit', page), queryFn: ({ signal }) => api<Page<AuditEvent>>('/admin/audit-events', { query: { page, page_size: 25 }, signal }), placeholderData: keepPreviousData })
export const useConfig = () => useQuery({ queryKey: qk.admin('config'), queryFn: ({ signal }) => api<Item<Config>>('/admin/configuration', { signal }).then((r) => r.data) })
export const useJobHealth = () =>
  useQuery({ queryKey: qk.admin('job-health'), queryFn: ({ signal }) => api<Item<{ by_status: Record<string, number>; stale_running: number; oldest_queued_at: string | null }>>('/admin/job-health', { signal }).then((r) => r.data), refetchInterval: 10_000 })
export const useReview = (q: Query) =>
  useQuery({ queryKey: qk.review(q), queryFn: ({ signal }) => api<Page<ReviewItem>>('/review-queue', { query: q, signal }), placeholderData: keepPreviousData })

export function useUserAction() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, action }: { id: string; action: 'revoke-sessions' | 'password-reset' }) => api<Item<unknown>>(`/admin/users/${id}/${action}`, { method: 'POST' }),
    onSuccess: () => (qc.invalidateQueries({ queryKey: qk.admin('users') }), qc.invalidateQueries({ queryKey: ['invitations'] })),
  })
}
export function useUpdateUser() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: UserUpdate }) => api<Item<User>>(`/admin/users/${id}`, { method: 'PATCH', body }),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.admin('users') }),
  })
}
export function useUpdateConfig() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: ConfigUpdate) => api<Item<Config>>('/admin/configuration', { method: 'PATCH', body }),
    onSuccess: (r) => qc.setQueryData(qk.admin('config'), r.data),
  })
}
export function useResolveReview() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, review_status, resolution_note }: { id: number; review_status: 'resolved' | 'dismissed' | 'open'; resolution_note?: string }) =>
      api<Item<ReviewItem>>(`/review-queue/${id}`, { method: 'PATCH', body: { review_status, resolution_note } }),
    onSuccess: () => (qc.invalidateQueries({ queryKey: ['review'] }), qc.invalidateQueries({ queryKey: ['dashboard'] })),
  })
}
