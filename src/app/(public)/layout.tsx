import { PlatformProviders } from '@/components/platform/PlatformProviders'
import { PublicShell } from '@/components/public/PublicShell'

export default function PublicLayout({ children }: { children: React.ReactNode }) {
  return (
    <PlatformProviders>
      <PublicShell>{children}</PublicShell>
    </PlatformProviders>
  )
}
