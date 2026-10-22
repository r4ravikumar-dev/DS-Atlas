import { PlatformProviders } from '@/components/platform/PlatformProviders'
import { SiteHeader } from '@/components/navigation/SiteHeader'
import { SiteFooter } from '@/components/layout/SiteFooter'

/** Public directory chrome. No account is needed for anything rendered inside. */
export default function PublicLayout({ children }: { children: React.ReactNode }) {
  return (
    <PlatformProviders>
      <a href="#main" className="focus-ring sr-only z-50 rounded-sm bg-accent px-4 py-2 text-accent-ink focus:not-sr-only focus:fixed focus:top-3 focus:left-3">Skip to content</a>
      <div className="flex min-h-screen flex-col">
        <SiteHeader />
        <main id="main" className="flex-1">{children}</main>
        <SiteFooter />
      </div>
    </PlatformProviders>
  )
}
