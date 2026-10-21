import Link from 'next/link'

export default function NotFound() {
  return (
    <section className="container" style={{ minHeight: '80vh', display: 'grid', placeContent: 'center', textAlign: 'center', gap: 20 }}>
      <p className="mono" style={{ color: 'var(--muted)' }}>
        404 — off the map
      </p>
      <h1 style={{ fontSize: 'clamp(3rem, 10vw, 8rem)' }}>
        Uncharted <span className="serif" style={{ color: 'var(--accent-text)' }}>territory</span>
      </h1>
      <Link href="/" style={{ borderBottom: '1px solid var(--accent)', justifySelf: 'center' }}>
        Back to the atlas
      </Link>
    </section>
  )
}
