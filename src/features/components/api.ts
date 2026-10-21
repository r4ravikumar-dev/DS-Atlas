'use client'

import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { api, type Query } from '@/lib/api/client'
import { qk } from '@/lib/api/keys'
import type { Component, ComponentDetail, Evidence, Facet, Guideline, Item, Page, Token } from '@/lib/api/types'

export interface ComponentFacets { families: Facet[]; libraries: Facet[]; detail_levels: Facet[] }

export const useComponents = (q: Query, enabled = true) =>
  useQuery({ queryKey: qk.components(q), queryFn: ({ signal }) => api<Page<Component>>('/components', { query: q, signal }), placeholderData: keepPreviousData, enabled })
export const useComponentFacets = () =>
  useQuery({ queryKey: qk.facets('components'), queryFn: ({ signal }) => api<Item<ComponentFacets>>('/components/facets', { signal }).then((r) => r.data), staleTime: 300_000 })
export const useComponent = (id: number) =>
  useQuery({ queryKey: qk.component(id), queryFn: ({ signal }) => api<Item<ComponentDetail>>(`/components/${id}`, { signal }).then((r) => r.data) })
export const useComponentEvidence = (id: number) =>
  useQuery({ queryKey: qk.component(id, 'evidence'), queryFn: ({ signal }) => api<Page<Evidence>>(`/components/${id}/evidence`, { signal }).then((r) => r.data) })
export const useRelatedComponents = (id: number) =>
  useQuery({ queryKey: qk.component(id, 'related'), queryFn: ({ signal }) => api<Page<Component>>(`/components/${id}/related-components`, { signal }).then((r) => r.data) })
export const useRelatedGuidelines = (id: number) =>
  useQuery({ queryKey: qk.component(id, 'guidelines'), queryFn: ({ signal }) => api<Page<Guideline>>(`/components/${id}/related-guidelines`, { signal }).then((r) => r.data) })
export const useRelatedTokens = (id: number) =>
  useQuery({ queryKey: qk.component(id, 'tokens'), queryFn: ({ signal }) => api<Page<Token>>(`/components/${id}/related-tokens`, { signal }).then((r) => r.data) })
