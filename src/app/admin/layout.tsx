import type { Metadata } from 'next'
import { PlatformProviders } from '@/components/platform/PlatformProviders'
import { Shell } from '@/components/platform/Shell'

export const metadata: Metadata = {
  title: { default: 'Administration', template: '%s · Admin · Design Systems Directory' },
  description: 'Private administration of the design-systems directory.',
  robots: { index: false, follow: false, nocache: true },
}

export default function PlatformLayout({ children }: { children: React.ReactNode }) {
  return (
    <PlatformProviders>
      <Shell>{children}</Shell>
    </PlatformProviders>
  )
}
