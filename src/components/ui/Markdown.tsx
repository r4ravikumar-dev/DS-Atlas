'use client'

import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import s from './Markdown.module.scss'

/** Renders backend-generated Markdown. Raw HTML is not rendered (react-markdown default) and links open safely. */
export function Markdown({ children }: { children: string }) {
  return (
    <div className={s.md}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ href, children: c }) =>
            href?.startsWith('http') ? (
              <a href={href} target="_blank" rel="noopener noreferrer nofollow">
                {c}
              </a>
            ) : (
              <a href={href}>{c}</a>
            ),
          table: ({ children: c }) => (
            <div className={s.tableWrap}>
              <table>{c}</table>
            </div>
          ),
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  )
}
