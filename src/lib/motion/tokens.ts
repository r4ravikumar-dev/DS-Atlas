/**
 * Motion tokens — one timing language for Motion for React, GSAP and CSS (mirrored as --dur-* / --ease-* in tokens.css).
 * Components import these instead of inventing their own durations, easings or springs.
 */
export const duration = { instant: 0.12, fast: 0.2, base: 0.32, slow: 0.6, hero: 1.1 } as const

export const ease = {
  out: [0.22, 1, 0.36, 1],
  inOut: [0.65, 0, 0.35, 1],
  emphasized: [0.16, 1, 0.3, 1],
} as const

/** GSAP equivalents of the cubic-béziers above. */
export const gsapEase = { out: 'power3.out', inOut: 'power2.inOut', emphasized: 'expo.out' } as const

export const spring = {
  /** buttons, toggles, active indicators */
  snappy: { type: 'spring', stiffness: 520, damping: 34, mass: 0.7 },
  /** cards, popovers, sheets */
  gentle: { type: 'spring', stiffness: 220, damping: 26 },
  /** layout and shared-element transitions */
  layout: { type: 'spring', stiffness: 320, damping: 32 },
} as const

export const stagger = { tight: 0.035, base: 0.06, loose: 0.1 } as const

export const distance = { sm: 8, md: 16, lg: 32 } as const

export const hover = { lift: -3, scale: 1.015, press: 0.97 } as const

/** Scroll reveals fire once, slightly before the element is fully on screen. */
export const viewport = { once: true, amount: 0.2, margin: '0px 0px -8% 0px' } as const

/** Lists can be taller than the screen, so they start as soon as their top edge comes into view. */
export const viewportList = { once: true, amount: 0, margin: '0px 0px -6% 0px' } as const
