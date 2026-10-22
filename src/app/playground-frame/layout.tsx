import type { Metadata } from 'next'

export const metadata: Metadata = { title: 'Component preview', robots: { index: false, follow: false } }

/** Bare document for the sandboxed component preview: no site chrome, embedded only by this site's playground pages. */
export default function FrameLayout({ children }: { children: React.ReactNode }) {
  return children
}
