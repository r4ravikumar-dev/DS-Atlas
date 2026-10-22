import { notFound, permanentRedirect } from 'next/navigation'
import { BackendError, getItem } from '@/lib/api/server'

/** Old global token URLs now live inside their design system: /systems/{system}/tokens/{token}. */
export default async function TokenRedirect({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  if (!/^\d{1,9}$/.test(id)) notFound()
  let t: { slug?: string | null; system_slug?: string | null }
  try {
    t = await getItem(`/tokens/${id}`, { tags: [`token:${id}`] })
  } catch (e) {
    if (e instanceof BackendError && e.status === 404) notFound()
    throw e
  }
  if (!t.system_slug || !t.slug) notFound()
  permanentRedirect(`/systems/${t.system_slug}/tokens/${t.slug}`)
}
