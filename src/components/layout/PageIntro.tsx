import { cn } from '@/lib/cn'

/** Page header: eyebrow, editorial title, short description, optional aside (e.g. counts or actions). */
export function PageIntro({ eyebrow, title, accent, description, aside, className }: {
  eyebrow: string; title: string; accent?: string; description?: React.ReactNode; aside?: React.ReactNode; className?: string
}) {
  return (
    <header className={cn('border-b border-line', className)}>
      <div className="container-page flex flex-col gap-8 pt-14 pb-10 md:flex-row md:items-end md:justify-between md:pt-20">
        <div className="max-w-3xl">
          <p className="eyebrow mb-4">{eyebrow}</p>
          <h1 className="text-title font-medium">
            {title}{accent && <> <span className="font-serif font-normal text-muted italic">{accent}</span></>}
          </h1>
          {description && <p className="measure mt-5 text-lg text-text-2">{description}</p>}
        </div>
        {aside}
      </div>
    </header>
  )
}
