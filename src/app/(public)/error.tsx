'use client'

import { useEffect } from 'react'
import { CloudOff } from 'lucide-react'
import { Button } from '@/components/kit/button'
import { BackToSite } from '@/components/kit/states'

/** A page-level failure is stated plainly; nothing stale or placeholder is shown in its place. */
export default function PublicError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => console.error(error), [error])
  return (
    <section className="container-page grid min-h-[60vh] content-center gap-6 py-20" role="alert">
      <CloudOff className="size-7 text-danger" aria-hidden />
      <h1 className="text-title font-medium">This page couldn&apos;t be loaded.</h1>
      <p className="measure text-lg text-text-2">The directory service didn&apos;t respond in time. The last published data is still there — try again in a moment.</p>
      <div className="flex flex-wrap items-center gap-2">
        <Button variant="primary" size="sm" onClick={reset}>Try again</Button>
        <BackToSite />
      </div>
      {error.digest && <p className="font-mono text-[0.7rem] text-faint">Reference {error.digest}</p>}
    </section>
  )
}
