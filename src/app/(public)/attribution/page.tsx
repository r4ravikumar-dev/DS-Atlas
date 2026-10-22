import type { Metadata } from 'next'
import Link from 'next/link'

export const metadata: Metadata = {
  title: 'Attribution & intellectual property',
  description: 'Who owns the names, logos, images, components and documentation shown in the directory, and how they are used.',
  alternates: { canonical: '/attribution' },
}

const ITEMS: [string, React.ReactNode][] = [
  ['Names, logos and trademarks', 'Design-system names, organisation names, logos and trademarks belong to their respective owners. They are used only to identify each system. No affiliation, sponsorship or endorsement is implied unless explicitly stated.'],
  ['Logos and preview images', <>A system&apos;s icon or preview image is shown only when that system&apos;s own official website publishes it (its site icon or social-sharing image). The image is displayed from its original address — it is not copied to this site — and the page it came from is recorded and shown on the system&apos;s Resources page. When no such image exists, or it can&apos;t be loaded, a typographic monogram is shown instead; it is not a logo.</>],
  ['Licences', 'Reuse terms for these images are rarely stated by their publishers. The directory never assumes a licence: where a source states one, it is recorded; otherwise the image is referenced only for identification and research, and the rights remain entirely with the owner.'],
  ['Component previews', <>Interactive previews render each system&apos;s own open-source package, installed from the public npm registry at the version its documentation describes, under that package&apos;s licence. Where a system is distributed as copy-paste source (shadcn/ui), a clearly labelled platform-rendered preview follows its published, MIT-licensed recipes. Previews never use another system&apos;s components or images.</>],
  ['Documentation, tokens and examples', 'Component APIs, token values and guidance are short factual extracts from public documentation, always linked to their source. Read the official documentation for authoritative and complete guidance.'],
]

export default function Attribution() {
  return (
    <article className="container-page max-w-4xl pt-14 md:pt-20">
      <p className="eyebrow mb-4">Attribution</p>
      <h1 className="text-title font-medium">Their work, <span className="font-serif font-normal text-muted italic">credited as theirs.</span></h1>
      <dl className="mt-12 divide-y divide-line border-y border-line">
        {ITEMS.map(([k, v]) => (
          <div key={k} className="grid gap-2 py-6 md:grid-cols-[14rem_1fr]">
            <dt className="text-card font-medium">{k}</dt>
            <dd className="measure leading-relaxed text-text-2">{v}</dd>
          </div>
        ))}
      </dl>
      <p className="mt-8 text-meta text-muted">How records are collected and kept current is described in the <Link href="/about" className="focus-ring text-accent-text underline decoration-accent/40 underline-offset-4">methodology</Link>.</p>
    </article>
  )
}
