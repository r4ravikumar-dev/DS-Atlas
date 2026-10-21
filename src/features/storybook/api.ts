'use client'

import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, type Query } from '@/lib/api/client'
import { qk } from '@/lib/api/keys'
import type { Item, Page, StorybookProject, StorybookStory, StorybookVariant } from '@/lib/api/types'

export function useStorybookProjects(q?: Query) {
  return useQuery({
    queryKey: qk.storybook('projects', q),
    queryFn: ({ signal }) => api<Page<StorybookProject>>('/storybook/projects', { query: q, signal }),
    placeholderData: keepPreviousData,
  })
}

export function useStorybookProject(id: number) {
  return useQuery({
    queryKey: qk.storybook('project', id),
    queryFn: ({ signal }) => api<Item<StorybookProject>>(`/storybook/projects/${id}`, { signal }).then((r) => r.data),
    enabled: Number.isFinite(id) && id > 0,
  })
}

export function useStorybookStories(q?: Query) {
  return useQuery({
    queryKey: qk.storybook('stories', q),
    queryFn: ({ signal }) => api<Page<StorybookStory>>('/storybook/stories', { query: q, signal }),
    placeholderData: keepPreviousData,
  })
}

export function useStorybookStory(id: number) {
  return useQuery({
    queryKey: qk.storybook('story', id),
    queryFn: ({ signal }) => api<Item<StorybookStory>>(`/storybook/stories/${id}`, { signal }).then((r) => r.data),
    enabled: Number.isFinite(id) && id > 0,
  })
}

export function useStorybookVariants(q?: Query) {
  return useQuery({
    queryKey: qk.storybook('variants', q),
    queryFn: ({ signal }) => api<Page<StorybookVariant>>('/storybook/variants', { query: q, signal }),
    placeholderData: keepPreviousData,
  })
}

export function useCrawlStorybook() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (refresh: boolean = false) =>
      api<Item<{ job_ids: string[] }>>('/storybook/crawl', { method: 'POST', query: { refresh } }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['storybook'] })
      qc.invalidateQueries({ queryKey: ['jobs'] })
    },
  })
}
