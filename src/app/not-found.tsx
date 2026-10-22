import Link from 'next/link'

export default function NotFound() {
  return (
    <section style={{ minHeight: '80vh', display: 'grid', placeContent: 'center', textAlign: 'center', gap: 16 }}>
      <p className="mono" style={{ color: 'var(--muted)' }}>404</p>
      <h1>Page not found</h1>
      <Link href="/platform" style={{ borderBottom: '1px solid var(--accent)', justifySelf: 'center' }}>
        Back to the dashboard
      </Link>
    </section>
  )
}
