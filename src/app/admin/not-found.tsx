import Link from 'next/link'

/** Unknown admin URL: administrators are sent back to the admin overview (public pages use "Back to Site" instead). */
export default function AdminNotFound() {
  return (
    <section style={{ minHeight: '60vh', display: 'grid', placeContent: 'center', textAlign: 'center', gap: 16 }}>
      <p className="mono" style={{ color: 'var(--muted)' }}>404</p>
      <h1>Admin page not found</h1>
      <Link href="/admin" style={{ borderBottom: '1px solid var(--accent)', justifySelf: 'center' }}>Back to admin overview</Link>
    </section>
  )
}
