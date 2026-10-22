import { CopyButton } from './copy-button'
import { cn } from '@/lib/cn'

/** Monospace block for verbatim documented values. Content is shown as text, never executed or rendered. */
export function CodeBlock({ code, label, className }: { code: string; label?: string; className?: string }) {
  return (
    <figure className={cn('overflow-hidden rounded-sm border border-line bg-bg-2', className)}>
      <figcaption className="flex items-center justify-between border-b border-line px-3 py-1.5">
        <span className="eyebrow">{label ?? 'Source'}</span>
        <CopyButton value={code} label="Copy code" />
      </figcaption>
      <pre tabIndex={0} className="focus-ring overflow-x-auto p-4 font-mono text-code leading-relaxed text-text-2"><code>{code}</code></pre>
    </figure>
  )
}
