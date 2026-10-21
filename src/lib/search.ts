import { SYSTEMS, CATEGORIES } from '@/data/systems'
import { DIRECTORIES, REPOS, RESOURCE_GROUPS, FOUNDATIONS } from '@/data/resources'
import { CHECKLIST } from '@/data/checklist'

export type SearchKind = 'Page' | 'System' | 'Directory' | 'Repo' | 'Resource' | 'Foundation' | 'Checklist'

export interface SearchEntry {
  id: string
  kind: SearchKind
  title: string
  subtitle: string
  href: string
  external?: boolean
  keywords?: string
}

export const PAGES: SearchEntry[] = [
  { id: 'p-home', kind: 'Page', title: 'Atlas home', subtitle: 'Overview & strategy', href: '/' },
  { id: 'p-systems', kind: 'Page', title: 'Systems explorer', subtitle: `${SYSTEMS.length} company design systems`, href: '/systems' },
  { id: 'p-dirs', kind: 'Page', title: 'Directories & repos', subtitle: 'Meta-collections, awesome lists, token pipelines', href: '/directories' },
  { id: 'p-res', kind: 'Page', title: 'Resource library', subtitle: 'Tools, plugins, books, podcasts, articles', href: '/resources' },
  { id: 'p-found', kind: 'Page', title: 'Code foundations', subtitle: 'shadcn, Radix, Base UI, React Aria, Mantine, Ant', href: '/foundations' },
  { id: 'p-check', kind: 'Page', title: 'Design system checklist', subtitle: 'Track what your system covers', href: '/checklist' },
]

export function buildIndex(): SearchEntry[] {
  return [
    ...PAGES,
    ...SYSTEMS.map<SearchEntry>((s) => ({
      id: `s-${s.id}`,
      kind: 'System',
      title: `${s.company} — ${s.name}`,
      subtitle: s.strength,
      href: `/systems#${s.id}`,
      keywords: [CATEGORIES[s.category].label, ...s.stack, s.why ?? ''].join(' '),
    })),
    ...DIRECTORIES.map<SearchEntry>((d) => ({ id: `d-${d.name}`, kind: 'Directory', title: d.name, subtitle: d.desc, href: d.url, external: true })),
    ...REPOS.map<SearchEntry>((d) => ({ id: `r-${d.name}`, kind: 'Repo', title: d.name, subtitle: d.desc, href: d.url, external: true })),
    ...RESOURCE_GROUPS.flatMap((g) =>
      g.items.map<SearchEntry>((r) => ({
        id: `res-${g.id}-${r.name}`,
        kind: 'Resource',
        title: r.name,
        subtitle: `${g.title} · ${r.desc}`,
        href: r.url,
        external: true,
        keywords: r.meta,
      })),
    ),
    ...FOUNDATIONS.map<SearchEntry>((f) => ({ id: `f-${f.id}`, kind: 'Foundation', title: f.name, subtitle: f.tagline + ' · ' + f.bestFor, href: `/foundations#${f.id}` })),
    ...CHECKLIST.flatMap((c) =>
      c.sections.map<SearchEntry>((s) => ({
        id: `c-${c.id}-${s.id}`,
        kind: 'Checklist',
        title: `${s.title}`,
        subtitle: `${c.title} · ${s.items.length} checks`,
        href: `/checklist?c=${c.id}#${s.id}`,
        keywords: s.items.map((i) => i.title).join(' '),
      })),
    ),
  ]
}
