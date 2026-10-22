import Link from 'next/link'
import { Wordmark } from '@/components/navigation/Wordmark'
import { BackToSite, RecoveryLink } from '@/components/kit/states'

export default function NotFound() {
  return (
    <main className="container-page grid min-h-svh content-center gap-8 py-20">
      <Link href="/" className="focus-ring w-fit"><Wordmark /></Link>
      <p className="font-mono text-meta text-muted">404</p>
      <h1 className="text-title font-medium">This page isn&apos;t in the index <span className="font-serif font-normal text-muted italic">— yet.</span></h1>
      <p className="measure text-lg text-text-2">The record may have been merged into another one, or the address is mistyped.</p>
      <div className="flex flex-wrap items-center gap-2"><BackToSite /><RecoveryLink href="/systems">Browse design systems</RecoveryLink></div>
    </main>
  )
}
