import type { DesignSystem } from '@/data/systems'

export const TOKEN_TAGS = ['Tokens', 'Style Dictionary', 'W3C Tokens', 'Tokens Studio']
export const hasTokens = (s: DesignSystem) => s.stack.some((t) => TOKEN_TAGS.includes(t))
export const frameworkTags = (s: DesignSystem) => s.stack.filter((t) => !TOKEN_TAGS.includes(t))

export const SOURCE_LABEL = { open: 'Open source', hybrid: 'Public docs', closed: 'Closed' } as const

export const CATEGORY_COLOR: Record<DesignSystem['category'], string> = {
  enterprise: 'var(--sky)',
  saas: 'var(--violet)',
  consumer: 'var(--coral)',
  public: 'var(--mint)',
  platform: 'var(--accent)',
  library: 'var(--amber)',
  industry: 'var(--pink)',
}

export const initials = (s: DesignSystem) =>
  s.company
    .replace(/[^A-Za-z0-9 ]/g, ' ')
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0])
    .join('')
    .toUpperCase()
