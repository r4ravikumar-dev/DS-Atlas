import { BookOpen, FolderGit2, Globe, Layers, Link2, PenTool, ShieldCheck } from 'lucide-react'
import type { ResourceLink, ResourceType } from '@/lib/api/types'
import s from './ResourceLinks.module.scss'

export const RESOURCE_LABEL: Record<ResourceType, string> = {
  official_website: 'Official website',
  official_documentation: 'Documentation',
  github_repository: 'GitHub repository',
  figma_file: 'Figma file',
  storybook: 'Storybook',
  additional_resource: 'Additional resource',
}
const SHORT: Record<ResourceType, string> = {
  official_website: 'Website', official_documentation: 'Docs', github_repository: 'GitHub', figma_file: 'Figma', storybook: 'Storybook', additional_resource: 'Link',
}
const ICON: Record<ResourceType, typeof Globe> = {
  official_website: Globe, official_documentation: BookOpen, github_repository: FolderGit2, figma_file: PenTool, storybook: Layers, additional_resource: Link2,
}

/**
 * Renders only links that exist. A verified link carries a check mark; an unverified one is labelled as directory-listed.
 * External links open in a new tab without opener access or a referrer.
 */
export function ResourceLinks({ links, compact = false, exclude = ['additional_resource'] }: { links: ResourceLink[]; compact?: boolean; exclude?: ResourceType[] }) {
  const shown = links.filter((l) => !exclude.includes(l.type))
  if (shown.length === 0) return null
  return (
    <ul className={s.links} aria-label="Resources">
      {shown.map((l) => {
        const Icon = ICON[l.type]
        const label = compact ? SHORT[l.type] : RESOURCE_LABEL[l.type]
        return (
          <li key={l.type + l.url}>
            <a
              href={l.url}
              target="_blank"
              rel="noopener noreferrer nofollow"
              referrerPolicy="no-referrer"
              className={s.link}
              data-verified={l.verified || undefined}
              title={`${RESOURCE_LABEL[l.type]} — ${l.verified ? 'verified' : 'listed by a directory, not yet verified'}: ${l.url}`}
              onClick={(e) => e.stopPropagation()}
            >
              <Icon size={13} aria-hidden />
              {label}
              {l.verified ? <ShieldCheck size={12} aria-label="verified" className={s.check} /> : <span className={s.unv}>unverified</span>}
            </a>
          </li>
        )
      })}
    </ul>
  )
}
