import { clsx, type ClassValue } from 'clsx'
import { extendTailwindMerge } from 'tailwind-merge'

// Teach tailwind-merge the custom type scale so `text-display` isn't mistaken for a colour and dropped next to `text-muted`.
const twMerge = extendTailwindMerge({
  extend: { theme: { text: ['display', 'title', 'section', 'card', 'meta', 'code', 'caption'] } },
})

/** Merge class names, letting later Tailwind utilities win over earlier conflicting ones. */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
