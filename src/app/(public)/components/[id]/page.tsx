import { notFound, permanentRedirect } from 'next/navigation'
import { BackendError, getItem } from '@/lib/api/server'

/** Old global component URLs now live inside their design system: /systems/{system}/components/{component}. */
export default async function ComponentRedirect({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  if (!/^\d{1,9}$/.test(id)) notFound()
  let c: { slug?: string | null; system_slug?: string | null }
  try {
    c = await getItem(`/components/${id}`, { tags: [`component:${id}`] })
  } catch (e) {
    if (e instanceof BackendError && e.status === 404) notFound()
    throw e
  }
  if (!c.system_slug || !c.slug) notFound()
  permanentRedirect(`/systems/${c.system_slug}/components/${c.slug}`)
}
