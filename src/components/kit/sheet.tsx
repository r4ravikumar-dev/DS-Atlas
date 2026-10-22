'use client'

import { Dialog } from 'radix-ui'
import { AnimatePresence, motion } from 'motion/react'
import { X } from 'lucide-react'
import { spring } from '@/lib/motion/tokens'
import { cn } from '@/lib/cn'

/** Side sheet on Radix Dialog (focus trap, Escape, aria) with a spring entrance. */
export function Sheet({ open, onOpenChange, title, description, side = 'right', children, className }: {
  open: boolean; onOpenChange: (o: boolean) => void; title: string; description?: string; side?: 'left' | 'right'; children: React.ReactNode; className?: string
}) {
  const x = side === 'right' ? '100%' : '-100%'
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <AnimatePresence>
        {open && (
          <Dialog.Portal forceMount>
            <Dialog.Overlay asChild forceMount>
              <motion.div className="fixed inset-0 z-50 bg-overlay backdrop-blur-[2px]" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} />
            </Dialog.Overlay>
            <Dialog.Content asChild forceMount>
              <motion.div
                className={cn('fixed inset-y-0 z-50 flex w-[min(420px,92vw)] flex-col border-line bg-bg shadow-2 outline-none', side === 'right' ? 'right-0 border-l' : 'left-0 border-r', className)}
                initial={{ x }} animate={{ x: 0 }} exit={{ x }} transition={spring.gentle}
              >
                <div className="flex items-start justify-between gap-4 border-b border-line px-5 py-4">
                  <div>
                    <Dialog.Title className="text-card font-medium">{title}</Dialog.Title>
                    {description ? <Dialog.Description className="mt-1 text-meta text-muted">{description}</Dialog.Description> : <Dialog.Description className="sr-only">{title}</Dialog.Description>}
                  </div>
                  <Dialog.Close className="focus-ring -mr-2 grid size-9 place-items-center rounded-sm text-muted hover:bg-surface-2 hover:text-text" aria-label="Close">
                    <X className="size-4" />
                  </Dialog.Close>
                </div>
                <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-5 py-5">{children}</div>
              </motion.div>
            </Dialog.Content>
          </Dialog.Portal>
        )}
      </AnimatePresence>
    </Dialog.Root>
  )
}
