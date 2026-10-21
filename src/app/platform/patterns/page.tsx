'use client'

import { Suspense } from 'react'
import { GuidelineList } from '../guidelines/GuidelineList'

export default function PatternsPage() {
  return <Suspense><GuidelineList kind="patterns" /></Suspense>
}
