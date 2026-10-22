import { ExternalLink } from './external-link'

/** Render documentation text that may contain Markdown links `[label](https://…)` — links become safe external links, everything else stays text. */
export function InlineText({ text }: { text: string }) {
  const parts: React.ReactNode[] = []
  const re = /\[([^\]]{1,200})\]\((https?:\/\/[^\s)]{1,500})\)/g
  let last = 0
  for (let m = re.exec(text); m; m = re.exec(text)) {
    if (m.index > last) parts.push(text.slice(last, m.index))
    parts.push(<ExternalLink key={m.index} href={m[2]} className="text-accent-text">{m[1]}</ExternalLink>)
    last = m.index + m[0].length
  }
  parts.push(text.slice(last).replace(/<\/?Keyboard>/g, ''))
  return <>{parts}</>
}
