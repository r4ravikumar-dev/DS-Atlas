import type { Metadata } from 'next'

export const metadata: Metadata = { title: 'Privacy', description: 'What the public directory does and does not collect about visitors.', alternates: { canonical: '/privacy' } }

export default function Privacy() {
  return (
    <article className="container-page max-w-4xl pt-14 md:pt-20">
      <p className="eyebrow mb-4">Privacy</p>
      <h1 className="text-title font-medium">Browse without an account.</h1>
      <ul className="measure mt-10 flex list-disc flex-col gap-4 pl-5 leading-relaxed text-text-2">
        <li>The public directory needs no account and sets no tracking or advertising cookies. Your theme and reduce-motion choices are stored only in your own browser.</li>
        <li>Requests are rate-limited per network address to keep the service available; server logs record the request path, status and timing for operating the service.</li>
        <li>Logos and preview images are loaded from each design system&apos;s own website, so your browser contacts those sites when they are shown (no referrer is sent).</li>
        <li>Interactive previews run entirely in your browser; nothing you type into a playground is sent to the server.</li>
        <li>Links to official websites, repositories, Figma files and Storybooks take you to those services, which have their own policies.</li>
      </ul>
    </article>
  )
}
