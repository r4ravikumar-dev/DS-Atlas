import '@testing-library/jest-dom/vitest'
import { afterEach, vi } from 'vitest'
import { cleanup } from '@testing-library/react'

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

// jsdom lacks these browser APIs used by motion preferences, scroll-spy and in-view reveals.
if (!window.matchMedia) {
  window.matchMedia = (query: string) =>
    ({ matches: false, media: query, onchange: null, addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {}, dispatchEvent: () => false }) as MediaQueryList
}
if (!('IntersectionObserver' in window)) {
  class IO { observe() {} unobserve() {} disconnect() {} takeRecords() { return [] } root = null; rootMargin = ''; thresholds = [] }
  ;(window as unknown as { IntersectionObserver: unknown }).IntersectionObserver = IO
  ;(globalThis as unknown as { IntersectionObserver: unknown }).IntersectionObserver = IO
}
