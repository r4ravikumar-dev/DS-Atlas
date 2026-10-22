/**
 * Hero illustration: a design-system "specimen sheet" — the things this directory catalogues (colour tokens, a type
 * scale, spacing, and components with their variants and states), drawn from plain HTML in the site's own tokens.
 * It is decorative (aria-hidden), contains no claims about any real system, and only fades in once (CSS; off with
 * reduced motion).
 */
export function HeroIllustration() {
  return (
    <div aria-hidden className="relative mx-auto grid w-full max-w-[34rem] select-none grid-cols-6 gap-3 text-text [&>*]:animate-[rise_0.8s_var(--ease-out)_both]">
      {/* colour tokens */}
      <Panel className="col-span-4 [animation-delay:60ms]" label="Colour">
        <div className="grid grid-cols-5 gap-1.5">
          {['--accent', '--violet', '--sky', '--mint', '--coral'].map((c) => (
            <div key={c} className="flex flex-col gap-1.5">
              <span className="aspect-square rounded-xs" style={{ background: `var(${c})` }} />
              <span className="h-1 w-3/4 rounded-full bg-line-strong" />
            </div>
          ))}
        </div>
      </Panel>

      {/* type */}
      <Panel className="col-span-2 row-span-2 [animation-delay:140ms]" label="Type">
        <div className="flex h-full flex-col justify-between gap-3">
          <span className="font-serif text-[3.25rem] leading-none italic">Aa</span>
          <div className="flex flex-col gap-1.5">
            {[100, 78, 60, 44].map((w) => <span key={w} className="h-1.5 rounded-full bg-text/70" style={{ width: `${w}%` }} />)}
          </div>
        </div>
      </Panel>

      {/* spacing */}
      <Panel className="col-span-4 [animation-delay:220ms]" label="Spacing">
        <div className="flex items-end gap-2">
          {[4, 8, 12, 16, 24, 32].map((n) => (
            <span key={n} className="rounded-[2px] bg-violet/70" style={{ width: n, height: n }} />
          ))}
        </div>
      </Panel>

      {/* components */}
      <Panel className="col-span-6 [animation-delay:300ms]" label="Components">
        <div className="grid gap-4 sm:grid-cols-[1.2fr_1fr]">
          <div className="flex flex-col gap-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex h-8 items-center rounded-sm bg-accent px-3.5 text-[0.8rem] font-medium text-accent-ink">Primary</span>
              <span className="inline-flex h-8 items-center rounded-sm border border-line-strong px-3.5 text-[0.8rem]">Secondary</span>
              <span className="inline-flex h-8 items-center rounded-sm px-2 text-[0.8rem] text-muted">Ghost</span>
            </div>
            <div className="flex flex-col gap-1.5">
              <span className="h-1.5 w-12 rounded-full bg-line-strong" />
              <span className="flex h-9 items-center rounded-sm border border-line-strong px-3 text-[0.78rem] text-faint">name@company.com</span>
            </div>
          </div>
          <div className="flex flex-col justify-between gap-3">
            <Row><Toggle on /><Bar w="55%" /></Row>
            <Row><Toggle /><Bar w="40%" /></Row>
            <Row><Check /><Bar w="65%" /></Row>
            <div className="h-1.5 rounded-full bg-line-strong"><div className="h-full w-3/5 rounded-full bg-accent" /></div>
          </div>
        </div>
      </Panel>
    </div>
  )
}

function Panel({ label, className, children }: { label: string; className?: string; children: React.ReactNode }) {
  return (
    <div className={`flex flex-col gap-3 rounded-md border border-line bg-surface/70 p-4 shadow-1 ${className ?? ''}`}>
      <span className="font-mono text-[0.62rem] tracking-[0.1em] text-muted uppercase">{label}</span>
      {children}
    </div>
  )
}

const Row = ({ children }: { children: React.ReactNode }) => <div className="flex items-center gap-2.5">{children}</div>
const Bar = ({ w }: { w: string }) => <span className="h-1.5 rounded-full bg-line-strong" style={{ width: w }} />
const Toggle = ({ on }: { on?: boolean }) => (
  <span className={`relative inline-block h-[18px] w-8 shrink-0 rounded-full ${on ? 'bg-accent' : 'bg-surface-3'}`}>
    <span className={`absolute top-[3px] size-3 rounded-full ${on ? 'left-[17px] bg-accent-ink' : 'left-[3px] bg-muted'}`} />
  </span>
)
const Check = () => (
  <span className="grid size-[18px] shrink-0 place-items-center rounded-[4px] bg-accent text-[11px] font-bold text-accent-ink">✓</span>
)
