import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

/**
 * A badge is a readout, not a control: nothing in this app gives one an
 * `onClick`. shadcn's variants ship a hover background at 80% alpha, and with
 * `--primary` at `0 0% 9%` that turned the timing, count and status badges
 * near-black under the cursor — promising an interaction that does not exist.
 * Call sites that pass
 * their own `bg-…` replaced the base colour through `tailwind-merge` but not the
 * `hover:` variant, which lives in a different modifier group, so the fix
 * belongs here rather than at each call site. An intentionally clickable badge
 * should ask for hover explicitly.
 *
 * `transition-colors` stays: the badges whose colour tracks state (the LATEST
 * review timer moving between live, paused and completed) still use it.
 */
const badgeVariants = cva(
  "inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-primary text-primary-foreground shadow",
        secondary:
          "border-transparent bg-secondary text-secondary-foreground",
        destructive:
          "border-transparent bg-destructive text-destructive-foreground shadow",
        outline: "text-foreground",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  )
}

export { Badge, badgeVariants }
