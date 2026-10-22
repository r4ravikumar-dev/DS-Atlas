'use client'

import { useState } from 'react'
import { cn } from '@/lib/cn'
import { Monogram } from '../catalog/Monogram'

interface Asset { url: string; alt?: string | null }

/**
 * The system's own published icon when one was found on its official site (referenced at its original URL, never
 * re-hosted); otherwise — or if the image fails to load — a typographic monogram. The box size is fixed, so there is no
 * layout shift either way.
 */
export function SystemLogo({ name, logo, size = 'md', className }: { name: string; logo?: Asset | null; size?: 'sm' | 'md' | 'lg'; className?: string }) {
  const [failed, setFailed] = useState(false)
  const box = { sm: 'size-9 p-1.5', md: 'size-12 p-2', lg: 'size-20 p-3' }[size]
  const px = { sm: 36, md: 48, lg: 80 }[size]
  if (!logo || failed) return <Monogram name={name} size={size} className={className} />
  return (
    // a neutral white plate: official marks are designed for light backgrounds
    <span className={cn('relative grid shrink-0 place-items-center overflow-hidden rounded-sm border border-line', box, className)} style={{ background: '#fff' }}>
      {/* eslint-disable-next-line @next/next/no-img-element -- arbitrary official hosts; see docs/design-system.md */}
      <img src={logo.url} alt={logo.alt || `${name} logo`} width={px} height={px} loading="lazy" decoding="async" referrerPolicy="no-referrer"
        onError={() => setFailed(true)} className="size-full object-contain" />
    </span>
  )
}
