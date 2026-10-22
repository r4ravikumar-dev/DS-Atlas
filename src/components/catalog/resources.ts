import { BookOpen, FolderGit2, Globe, Layers, Link2, PenTool } from 'lucide-react'
import type { ResourceType } from '@/lib/api/types'

export const RESOURCE_META: Record<ResourceType, { label: string; short: string; icon: typeof Globe; action: string }> = {
  official_website: { label: 'Official website', short: 'Website', icon: Globe, action: 'Visit official website' },
  official_documentation: { label: 'Documentation', short: 'Docs', icon: BookOpen, action: 'Read documentation' },
  github_repository: { label: 'GitHub repository', short: 'GitHub', icon: FolderGit2, action: 'Open GitHub' },
  figma_file: { label: 'Figma file', short: 'Figma', icon: PenTool, action: 'Open Figma' },
  storybook: { label: 'Storybook', short: 'Storybook', icon: Layers, action: 'View Storybook' },
  additional_resource: { label: 'Additional resource', short: 'Link', icon: Link2, action: 'Open link' },
}

export const PRIMARY_RESOURCES: ResourceType[] = ['official_website', 'official_documentation', 'github_repository', 'figma_file', 'storybook']
