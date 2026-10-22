import type { Metadata } from 'next'
import { PlatformProviders } from '@/components/platform/PlatformProviders'
import { Shell } from '@/components/platform/Shell'

export const metadata: Metadata = {
  title: { default: 'Knowledge Base', template: '%s · DS Knowledge Base' },
  description: 'Private administrator workspace for the design-systems knowledge base.',
  robots: { index: false, follow: false, nocache: true },
}

export default function PlatformLayout({ children }: { children: React.ReactNode }) {
  return (
    <PlatformProviders>
      <Shell>{children}</Shell>
    </PlatformProviders>
  )
}
