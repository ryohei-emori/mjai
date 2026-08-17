import { clsx, type ClassValue } from "clsx"
import { extendTailwindMerge } from "tailwind-merge"

/**
 * tailwind-merge only knows Tailwind's built-in scales. A value we added under
 * `theme.extend` is therefore unrecognised, and `text-body-base` falls through
 * to the colour group — where it displaces `text-on-primary` instead of the
 * base font size, leaving the element with the default body foreground. That is
 * what turned the New Session button's icon and label black.
 *
 * Registering the scales here fixes every call site at once, so a token can be
 * composed with a colour the obvious way. Keep these lists in step with
 * `tailwind.config.js`.
 */
const twMerge = extendTailwindMerge({
  extend: {
    theme: {
      text: [
        "headline-lg",
        "headline-md",
        "body-base",
        "body-sm",
        "metadata",
        "label-caps",
      ],
      spacing: [
        "container-margin",
        "card-gap",
        "gutter",
        "section",
        "topappbar",
      ],
    },
  },
})

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
