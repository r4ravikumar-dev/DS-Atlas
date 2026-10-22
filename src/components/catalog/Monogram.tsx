import { cn } from '@/lib/cn'

const TINTS = ['var(--accent)', 'var(--violet)', 'var(--sky)', 'var(--mint)', 'var(--amber)', 'var(--coral)', 'var(--pink)']

function hash(s: string) {
  let h = 0
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0
  return Math.abs(h)
}

export function initials(name: string) {
  const words = name.replace(/[^\p{L}\p{N}\s]/gu, ' ').split(/\s+/).filter(Boolean)
  if (words.length === 0) return '·'
  if (words.length === 1) return words[0].slice(0, 2)
  return (words[0][0] + words[1][0]).toUpperCase()
}

/**
 * Typographic identity for a system. We don't collect logos, so instead of inventing one we set the name's initials
 * on a tint derived from the name — consistent across the site, clearly not a brand mark.
 */
export function Monogram({ name, size = 'md', className }: { name: string; size?: 'sm' | 'md' | 'lg'; className?: string }) {
  const tint = TINTS[hash(name) % TINTS.length]
  const dims = { sm: 'size-9 text-[0.8rem]', md: 'size-12 text-base', lg: 'size-20 text-[1.6rem]' }[size]
  return (
    <span aria-hidden className={cn('relative grid shrink-0 place-items-center overflow-hidden rounded-sm border border-line font-serif italic', dims, className)}
      style={{ background: `color-mix(in oklab, ${tint} 14%, var(--surface))`, color: `color-mix(in oklab, ${tint} 75%, var(--text))` }}>
      {initials(name)}
    </span>
  )
}
