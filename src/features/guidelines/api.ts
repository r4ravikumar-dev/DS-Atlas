'use client'

import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { api, type Query } from '@/lib/api/client'
import { qk } from '@/lib/api/keys'
import type { Facet, Guideline, GuidelineDetail, Item, Page } from '@/lib/api/types'

export interface GuidelineFacets { categories: Facet[]; kinds: Facet[]; sources: Facet[] }
export type GKind = 'guidelines' | 'patterns'

export const useGuidelines = (kind: GKind, q: Query) =>
  useQuery({ queryKey: qk.guidelines(kind, q), queryFn: ({ signal }) => api<Page<Guideline>>(`/${kind}`, { query: q, signal }), placeholderData: keepPreviousData })
export const useGuidelineFacets = () =>
  useQuery({ queryKey: qk.facets('guidelines'), queryFn: ({ signal }) => api<Item<GuidelineFacets>>('/guidelines/facets', { signal }).then((r) => r.data), staleTime: 300_000 })
export const useGuideline = (kind: GKind, id: number) =>
  useQuery({ queryKey: qk.guideline(kind, id), queryFn: ({ signal }) => api<Item<GuidelineDetail>>(`/${kind}/${id}`, { signal }).then((r) => r.data) })
export interface RecordDetail { id: number; record_key: string; record_type: string; title: string; summary: string | null; primary_category: string; source_key: string; source_name: string;
  source_url: string; source_version: string | null; confidence: string; verification_status: string; is_stale: boolean; content: Record<string, unknown>; notes: string[];
  system_id: number | null; design_system_name: string | null; organization: string | null; last_verified_at: string | null;
  evidence: { id: number; url: string; excerpt: string | null; source_section: string | null; source_version: string | null; raw_document_id: number | null; captured_at: string }[] }
export const useRecord = (id: number) =>
  useQuery({ queryKey: qk.record(id), queryFn: ({ signal }) => api<Item<RecordDetail>>(`/records/${id}`, { signal }).then((r) => r.data) })
