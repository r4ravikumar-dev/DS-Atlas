import { previewKind, toMs, toPx, tokenValue, type TokenLike } from '@/lib/tokens/preview'
import { cn } from '@/lib/cn'

/**
 * Visual sample for a token whose stored value is valid CSS of a known kind; renders nothing otherwise.
 * Values reach inline styles only after previewKind() has validated them against strict patterns.
 */
export function TokenSwatch({ token, className }: { token: TokenLike; className?: string }) {
  const kind = previewKind(token)
  const v = tokenValue(token)
  const box = 'inline-block shrink-0 rounded-xs border border-line align-middle'
  switch (kind) {
    case 'color':
      return <span aria-hidden className={cn(box, 'size-8 bg-[conic-gradient(var(--surface-2)_25%,var(--surface)_0_50%,var(--surface-2)_0_75%,var(--surface)_0)] bg-[length:8px_8px]', className)}><span className="block size-full rounded-[3px]" style={{ background: v }} /></span>
    case 'radius':
      return <span aria-hidden className={cn(box, 'size-8 border-0', className)}><span className="block size-full border-2 border-accent/70 bg-accent-soft" style={{ borderRadius: v }} /></span>
    case 'spacing':
    case 'dimension': {
      const px = Math.min(toPx(v) ?? 0, 96)
      return <span aria-hidden className="flex h-8 w-24 shrink-0 items-center"><span className="h-3 rounded-[2px] bg-violet/70" style={{ width: Math.max(px, 1) }} /></span>
    }
    case 'font-size':
      return <span aria-hidden className="grid h-8 w-12 shrink-0 place-items-center overflow-hidden leading-none text-text" style={{ fontSize: `min(${v}, 2rem)` }}>Aa</span>
    case 'font-weight':
      return <span aria-hidden className="grid h-8 w-12 shrink-0 place-items-center text-lg leading-none text-text" style={{ fontWeight: v as React.CSSProperties['fontWeight'] }}>Aa</span>
    case 'font-family':
      return <span aria-hidden className="grid h-8 w-12 shrink-0 place-items-center text-lg leading-none text-text" style={{ fontFamily: v }}>Aa</span>
    case 'shadow':
      return <span aria-hidden className={cn('inline-block size-8 shrink-0 rounded-xs bg-surface-2 align-middle', className)} style={{ boxShadow: v }} />
    case 'duration': {
      const ms = Math.min(toMs(v) ?? 0, 2000)
      return <span aria-hidden className="relative flex h-8 w-24 shrink-0 items-center"><span className="h-px w-full bg-line-strong" /><span className="absolute left-0 size-2 rounded-full bg-sky" style={{ animation: `token-slide ${Math.max(ms, 60)}ms var(--ease-in-out) infinite alternate` }} /></span>
    }
    case 'easing':
      return <span aria-hidden className="relative flex h-8 w-24 shrink-0 items-center"><span className="h-px w-full bg-line-strong" /><span className="absolute left-0 size-2 rounded-full bg-sky" style={{ animation: `token-slide 900ms ${v} infinite alternate` }} /></span>
    default:
      return null
  }
}
