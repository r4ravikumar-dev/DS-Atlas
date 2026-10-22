import { BackToSite, RecoveryLink } from '@/components/kit/states'

export default function PublicNotFound() {
  return (
    <section className="container-page grid min-h-[60vh] content-center gap-6 py-20">
      <p className="font-mono text-meta text-muted">404</p>
      <h1 className="text-title font-medium">Not in the index <span className="font-serif font-normal text-muted italic">— yet.</span></h1>
      <p className="measure text-lg text-text-2">This record doesn&apos;t exist, or it was merged into another one.</p>
      <div className="flex flex-wrap items-center gap-2"><BackToSite /><RecoveryLink href="/systems">Browse design systems</RecoveryLink><RecoveryLink href="/search">Search everything</RecoveryLink></div>
    </section>
  )
}
