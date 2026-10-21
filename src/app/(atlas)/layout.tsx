import { Header } from '@/components/Header'
import { Footer } from '@/components/Footer'
import { CommandPalette } from '@/components/CommandPalette'

/** Editorial Atlas shell (curated guide pages). Research data lives in the API-backed /platform. */
export default function AtlasLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <a href="#main" className="sr-only">
        Skip to content
      </a>
      <Header />
      <main id="main">{children}</main>
      <Footer />
      <CommandPalette />
    </>
  )
}
