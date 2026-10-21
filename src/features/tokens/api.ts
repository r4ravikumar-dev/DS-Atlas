'use client'

import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { api, type Query } from '@/lib/api/client'
import { qk } from '@/lib/api/keys'
import type { Facet, Item, Page, Token } from '@/lib/api/types'

export interface TokenFacets { types: Facet[]; themes: Facet[]; platforms: Facet[]; groups: Facet[]; systems: Facet[] }
export type TokenDetail = Token & { record_key: string; source_url: string; source_section: string | null; value_note: string;
  evidence: { url: string; excerpt: string | null; source_version: string | null; raw_document_id: number | null }[]; extra: Record<string, unknown> }

export const useTokens = (q: Query) =>
  useQuery({ queryKey: qk.tokens(q), queryFn: ({ signal }) => api<Page<Token>>('/tokens', { query: q, signal }), placeholderData: keepPreviousData })
export const useTokenFacets = () =>
  useQuery({ queryKey: qk.facets('tokens'), queryFn: ({ signal }) => api<Item<TokenFacets>>('/tokens/facets', { signal }).then((r) => r.data), staleTime: 300_000 })
export const useToken = (id: number | null) =>
  useQuery({ queryKey: qk.token(id ?? 0), queryFn: ({ signal }) => api<Item<TokenDetail>>(`/tokens/${id}`, { signal }).then((r) => r.data), enabled: !!id })
export const useTokenRefs = (id: number | null, dir: 'references' | 'dependents') =>
  useQuery({ queryKey: qk.token(id ?? 0, dir), queryFn: ({ signal }) => api<Page<Token>>(`/tokens/${id}/${dir}`, { signal }).then((r) => r.data), enabled: !!id })
