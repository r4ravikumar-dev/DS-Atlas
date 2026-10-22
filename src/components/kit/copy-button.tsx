'use client'

import { useState } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { Check, Copy } from 'lucide-react'
import { duration } from '@/lib/motion/tokens'
import { cn } from '@/lib/cn'

export function CopyButton({ value, label = 'Copy', className }: { value: string; label?: string; className?: string }) {
  const [done, setDone] = useState(false)
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(value)
      setDone(true)
      setTimeout(() => setDone(false), 1400)
    } catch {}
  }
  return (
    <button type="button" onClick={copy} className={cn('focus-ring relative grid size-7 place-items-center rounded-xs text-muted transition-colors hover:bg-surface-2 hover:text-text', className)} aria-label={done ? 'Copied' : `${label} ${value}`}>
      <AnimatePresence mode="wait" initial={false}>
        <motion.span key={done ? 'y' : 'n'} initial={{ scale: 0.6, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.6, opacity: 0 }} transition={{ duration: duration.fast }}>
          {done ? <Check className="size-3.5 text-success" /> : <Copy className="size-3.5" />}
        </motion.span>
      </AnimatePresence>
      <span className="sr-only" aria-live="polite">{done ? 'Copied to clipboard' : ''}</span>
    </button>
  )
}
