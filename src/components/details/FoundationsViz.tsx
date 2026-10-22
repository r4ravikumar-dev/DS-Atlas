import Link from 'next/link'
import type { Token } from '@/lib/api/types'
import { groupFoundations, toMs, toPx, tokenValue } from '@/lib/tokens/preview'
import { CopyButton } from '../kit/copy-button'
import { TokenSwatch } from '../tokens/TokenPreview'

/** Group colour tokens by their documented group, or the path before the last separator (e.g. `color.text` / `--mantine-color-blue`). */
function colorFamily(t: Token) {
  if (t.group) return t.group
  const parts = t.path.replace(/^--/, '').split(/[.\-/_]/)
  return parts.length > 1 ? parts.slice(0, -1).join('-') : 'ungrouped'
}

/**
 * Foundations built only from collected values: colour swatches grouped by documented meaning, a type specimen,
 * proportional spacing and radius samples, elevation and motion. Tokens without a previewable value are not drawn.
 */
export function FoundationsViz({ tokens, base }: { tokens: Token[]; base: string }) {
  const href = (t: Token) => `${base}/tokens/${t.slug ?? t.id}`
  const groups = groupFoundations(tokens)
  if (groups.length === 0) return null
  return (
    <div className="flex flex-col gap-14">
      {groups.map((g) => (
        <section key={g.kind} aria-labelledby={`f-${g.kind}`}>
          <div className="mb-5 flex items-baseline justify-between gap-4 border-b border-line pb-3">
            <h3 id={`f-${g.kind}`} className="text-card font-medium">{g.label}</h3>
            <span className="font-mono text-meta text-muted">{g.tokens.length} {g.tokens.length === 1 ? 'token' : 'tokens'}</span>
          </div>
          {g.kind === 'color' ? <Colors tokens={g.tokens} href={href} />
            : g.kind === 'font-size' ? <TypeScale tokens={g.tokens} href={href} />
            : g.kind === 'spacing' ? <Spacing tokens={g.tokens} href={href} />
            : <Samples tokens={g.tokens} href={href} />}
        </section>
      ))}
      <p className="text-meta text-muted">
        Drawn from this system&apos;s stored tokens that hold a valid CSS value. <Link href={`${base}/tokens`} className="focus-ring text-accent-text underline decoration-accent/40 underline-offset-4 hover:decoration-accent">Inspect every token →</Link>
      </p>
    </div>
  )
}

/** Shared leading part of token paths (cut at a separator), so swatches can show the distinguishing tail: `blue-6`, not `--mantine-color-blu…`. */
function commonPrefix(paths: string[]) {
  if (paths.length < 2) return ''
  let p = paths[0]
  for (const x of paths) while (!x.startsWith(p)) p = p.slice(0, -1)
  const cut = Math.max(p.lastIndexOf('-'), p.lastIndexOf('.'), p.lastIndexOf('/'), p.lastIndexOf('_'))
  return cut > 0 ? p.slice(0, cut + 1) : ''
}

function Colors({ tokens, href }: { tokens: Token[]; href: (t: Token) => string }) {
  const fam = new Map<string, Token[]>()
  for (const t of tokens) fam.set(colorFamily(t), [...(fam.get(colorFamily(t)) ?? []), t])
  return (
    <div className="flex flex-col gap-8">
      {[...fam.entries()].map(([name, list]) => {
        const prefix = commonPrefix(list.map((t) => t.path))
        return (
        <div key={name}>
          <p className="eyebrow mb-3">{name}{prefix && <span className="ml-2 normal-case tracking-normal text-faint">{prefix}…</span>}</p>
          <ul className="grid grid-cols-[repeat(auto-fill,minmax(9.5rem,1fr))] gap-2">
            {list.map((t) => (
              <li key={t.id} className="group overflow-hidden rounded-sm border border-line bg-bg">
                <div className="h-16 border-b border-line" style={{ background: tokenValue(t) }} />
                <div className="flex items-start justify-between gap-1 p-2.5">
                  <div className="min-w-0">
                    <Link href={href(t)} className="focus-ring block truncate font-mono text-[0.7rem] text-text hover:text-accent-text" title={t.path}>{t.path.slice(prefix.length) || t.path}</Link>
                    <span className="block truncate font-mono text-[0.68rem] text-muted">{tokenValue(t)}{t.theme && t.theme !== 'default' ? ` · ${t.theme}` : ''}</span>
                  </div>
                  <CopyButton value={tokenValue(t)} label="Copy value" className="opacity-60 group-hover:opacity-100" />
                </div>
              </li>
            ))}
          </ul>
        </div>
        )
      })}
    </div>
  )
}

function TypeScale({ tokens, href }: { tokens: Token[]; href: (t: Token) => string }) {
  const sorted = [...tokens].sort((a, b) => (toPx(tokenValue(b)) ?? 0) - (toPx(tokenValue(a)) ?? 0))
  return (
    <ul className="divide-y divide-line">
      {sorted.map((t) => (
        <li key={t.id} className="grid items-baseline gap-2 py-3 md:grid-cols-[12rem_6rem_1fr]">
          <Link href={href(t)} className="focus-ring truncate font-mono text-[0.72rem] text-muted hover:text-text">{t.path}</Link>
          <span className="font-mono text-[0.72rem] text-text-2">{tokenValue(t)}</span>
          <span className="truncate leading-tight text-text" style={{ fontSize: `min(${tokenValue(t)}, 4rem)` }}>The quick brown fox</span>
        </li>
      ))}
    </ul>
  )
}

function Spacing({ tokens, href }: { tokens: Token[]; href: (t: Token) => string }) {
  const sorted = [...tokens].sort((a, b) => (toPx(tokenValue(a)) ?? 0) - (toPx(tokenValue(b)) ?? 0))
  const max = Math.max(...sorted.map((t) => toPx(tokenValue(t)) ?? 0), 1)
  return (
    <ul className="flex flex-col gap-2">
      {sorted.map((t) => (
        <li key={t.id} className="grid grid-cols-[minmax(0,10rem)_4.5rem_1fr] items-center gap-3">
          <Link href={href(t)} className="focus-ring truncate font-mono text-[0.72rem] text-muted hover:text-text">{t.path}</Link>
          <span className="font-mono text-[0.72rem] text-text-2">{tokenValue(t)}</span>
          <span className="h-3 rounded-[2px] bg-violet/70" style={{ width: `${Math.max(((toPx(tokenValue(t)) ?? 0) / max) * 100, 0.5)}%` }} aria-hidden />
        </li>
      ))}
    </ul>
  )
}

function Samples({ tokens, href }: { tokens: Token[]; href: (t: Token) => string }) {
  const sorted = [...tokens].sort((a, b) => (toPx(tokenValue(a)) ?? toMs(tokenValue(a)) ?? 0) - (toPx(tokenValue(b)) ?? toMs(tokenValue(b)) ?? 0))
  return (
    <ul className="grid grid-cols-[repeat(auto-fill,minmax(14rem,1fr))] gap-3">
      {sorted.map((t) => (
        <li key={t.id} className="flex items-center gap-3 rounded-sm border border-line p-3">
          <TokenSwatch token={t} />
          <div className="min-w-0">
            <Link href={href(t)} className="focus-ring block truncate font-mono text-[0.72rem] text-text hover:text-accent-text">{t.path}</Link>
            <span className="block truncate font-mono text-[0.68rem] text-muted">{tokenValue(t)}</span>
          </div>
        </li>
      ))}
    </ul>
  )
}
