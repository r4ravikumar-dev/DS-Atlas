import type { Metadata } from 'next'
import { PlatformProviders } from '@/components/platform/PlatformProviders'
import { Shell } from '@/components/platform/Shell'

export const metadata: Metadata = {
  title: { default: 'Research Platform', template: '%s · DS Research Platform' },
  description: 'Backend-managed design-systems research data: sources, crawl jobs, systems, components, tokens, guidelines, comparisons and reports.',
}

export default function PlatformLayout({ children }: { children: React.ReactNode }) {
  return (
    <PlatformProviders>
      <Shell>{children}</Shell>
    </PlatformProviders>
  )
}
