'use client'

import { Tooltip as T } from 'radix-ui'

export function Tooltip({ content, children }: { content: React.ReactNode; children: React.ReactElement }) {
  return (
    <T.Provider delayDuration={250}>
      <T.Root>
        <T.Trigger asChild>{children}</T.Trigger>
        <T.Portal>
          <T.Content sideOffset={6} className="z-50 max-w-64 rounded-xs border border-line-strong bg-surface-2 px-2.5 py-1.5 text-meta text-text shadow-1">
            {content}
          </T.Content>
        </T.Portal>
      </T.Root>
    </T.Provider>
  )
}
