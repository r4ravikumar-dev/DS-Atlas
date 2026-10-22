import type { Metadata } from 'next'
import { loadResearch, ResearchDetail } from '@/components/details/ResearchDetail'

type Params = { params: Promise<{ id: string }> }

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const g = await loadResearch('guidelines', (await params).id)
  return { title: g.title, description: (g.summary ?? `${g.category_name} research guidance.`).slice(0, 158), alternates: { canonical: `/guidelines/${g.id}` } }
}

export default async function ResearchPage({ params }: Params) {
  return <ResearchDetail g={await loadResearch('guidelines', (await params).id)} />
}
