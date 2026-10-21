'use client'

import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, type Query } from '@/lib/api/client'
import { qk } from '@/lib/api/keys'
import type { Component, Facet, Guideline, Item, Page, System, SystemDetail, Token } from '@/lib/api/types'

export interface SystemFacets { frameworks: Facet[]; sources: Facet[]; verification_status: Facet[] }
export interface SystemSourceRow { record_id: number; record_key: string; title: string; evidence_url: string; verification_status: string; source_id: number; source_key: string; source_name: string }

export const useSystems = (q: Query) =>
  useQuery({ queryKey: qk.systems(q), queryFn: ({ signal }) => api<Page<System>>('/design-systems', { query: q, signal }), placeholderData: keepPreviousData })
export const useSystemFacets = () =>
  useQuery({ queryKey: qk.facets('systems'), queryFn: ({ signal }) => api<Item<SystemFacets>>('/design-systems/facets', { signal }).then((r) => r.data), staleTime: 300_000 })
export const useSystem = (id: number) =>
  useQuery({ queryKey: qk.system(id), queryFn: ({ signal }) => api<Item<SystemDetail>>(`/design-systems/${id}`, { signal }).then((r) => r.data) })
export const useSystemComponents = (id: number, page: number) =>
  useQuery({ queryKey: qk.system(id, 'components', page), queryFn: ({ signal }) => api<Page<Component>>(`/design-systems/${id}/components`, { query: { page, page_size: 20 }, signal }), placeholderData: keepPreviousData })
export const useSystemTokens = (id: number, page: number) =>
  useQuery({ queryKey: qk.system(id, 'tokens', page), queryFn: ({ signal }) => api<Page<Token>>(`/design-systems/${id}/tokens`, { query: { page, page_size: 20 }, signal }), placeholderData: keepPreviousData })
export const useSystemGuidelines = (id: number, page: number) =>
  useQuery({ queryKey: qk.system(id, 'guidelines', page), queryFn: ({ signal }) => api<Page<Guideline>>(`/design-systems/${id}/guidelines`, { query: { page, page_size: 20 }, signal }), placeholderData: keepPreviousData })
export const useSystemSources = (id: number) =>
  useQuery({ queryKey: qk.system(id, 'sources'), queryFn: ({ signal }) => api<Item<SystemSourceRow[]>>(`/design-systems/${id}/sources`, { signal }).then((r) => r.data) })

export function useUpdateSystem(id: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { description?: string }) => api<Item<SystemDetail>>(`/design-systems/${id}`, { method: 'PATCH', body }),
    onSuccess: (r) => (qc.setQueryData(qk.system(id), r.data), qc.invalidateQueries({ queryKey: ['systems'] })),
  })
}
