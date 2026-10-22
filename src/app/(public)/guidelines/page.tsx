'use client'

import { Suspense } from 'react'
import { GuidelineList } from './GuidelineList'

export default function GuidelinesPage() {
  return <Suspense><GuidelineList kind="guidelines" /></Suspense>
}
