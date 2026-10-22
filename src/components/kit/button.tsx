import { Slot } from 'radix-ui'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/cn'

export const buttonVariants = cva(
  'focus-ring inline-flex shrink-0 items-center justify-center gap-2 whitespace-nowrap font-medium transition-[background-color,border-color,color,transform] duration-200 ease-out select-none active:scale-[0.97] disabled:pointer-events-none disabled:opacity-50 [&_svg]:shrink-0',
  {
    variants: {
      variant: {
        primary: 'bg-accent text-accent-ink hover:bg-text',
        secondary: 'border border-line-strong bg-surface text-text hover:border-text/40 hover:bg-surface-2',
        ghost: 'text-text-2 hover:bg-surface-2 hover:text-text',
        link: 'text-accent-text underline decoration-accent/40 underline-offset-4 hover:decoration-accent',
      },
      size: {
        sm: 'h-8 rounded-sm px-3 text-meta',
        md: 'h-10 rounded-sm px-4 text-[0.92rem]',
        lg: 'h-12 rounded-md px-6 text-base',
        icon: 'size-10 rounded-sm',
      },
    },
    defaultVariants: { variant: 'secondary', size: 'md' },
  },
)

export type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & VariantProps<typeof buttonVariants> & { asChild?: boolean }

/** Button, or any element styled as one with `asChild` (e.g. a Next <Link>). */
export function Button({ className, variant, size, asChild, ...props }: ButtonProps) {
  const Comp = asChild ? Slot.Root : 'button'
  return <Comp className={cn(buttonVariants({ variant, size }), className)} {...props} />
}
