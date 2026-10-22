'use client'

import { useApp } from '../Providers'

/** Site-level switch for decorative motion (the OS "reduce motion" setting is always honoured as well). */
export function MotionToggle() {
  const { motionOff, toggleMotion } = useApp()
  return (
    <button type="button" role="switch" aria-checked={motionOff} onClick={toggleMotion}
      className="focus-ring inline-flex items-center gap-2 rounded-sm text-meta text-muted hover:text-text">
      <span className={`relative h-4 w-7 rounded-full border border-line-strong transition-colors ${motionOff ? 'bg-accent' : 'bg-surface-2'}`} aria-hidden>
        <span className={`absolute top-0.5 size-2.5 rounded-full transition-[left,background-color] ${motionOff ? 'left-3.5 bg-accent-ink' : 'left-0.5 bg-muted'}`} />
      </span>
      Reduce motion
    </button>
  )
}
