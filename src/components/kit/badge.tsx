import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/cn'

export const badgeVariants = cva('inline-flex items-center gap-1 whitespace-nowrap rounded-xs border px-1.5 py-0.5 font-mono text-[0.7rem] leading-none', {
  variants: {
    tone: {
      neutral: 'border-line-strong text-text-2',
      muted: 'border-line text-muted',
      accent: 'border-transparent bg-accent-soft text-accent-text',
      success: 'border-success/30 text-success',
      warning: 'border-warning/30 text-warning',
      danger: 'border-danger/30 text-danger',
    },
  },
  defaultVariants: { tone: 'neutral' },
})

export function Badge({ className, tone, ...props }: React.HTMLAttributes<HTMLSpanElement> & VariantProps<typeof badgeVariants>) {
  return <span className={cn(badgeVariants({ tone }), className)} {...props} />
}
