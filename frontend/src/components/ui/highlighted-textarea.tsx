"use client"

import * as React from "react"
import { cn } from "@/lib/utils"

export type TextHighlightVariant = "hover" | "selected"

export type TextHighlight = {
  /** Substring to locate (first occurrence only) within the textarea's value. */
  text: string
  variant: TextHighlightVariant
}

type Segment = {
  text: string
  variant: TextHighlightVariant | null
}

/**
 * Resolves a list of substring highlights against `value` into contiguous
 * render segments. Matching is first-occurrence, exact-substring only; an
 * empty or unmatched highlight `text` is silently skipped (no error, no
 * highlight for that entry) — per the "graceful no-match" requirement.
 * Overlapping ranges resolve deterministically: "hover" takes priority over
 * "selected" (see design.md Decision 2).
 */
function computeSegments(value: string, highlights: TextHighlight[]): Segment[] {
  if (!value) return []

  const variantPerIndex: (TextHighlightVariant | null)[] = new Array(value.length).fill(null)

  // Apply "selected" first so "hover" (applied second) wins on overlap.
  const ordered = [
    ...highlights.filter((h) => h.variant === "selected"),
    ...highlights.filter((h) => h.variant === "hover"),
  ]

  for (const highlight of ordered) {
    if (!highlight.text) continue
    const start = value.indexOf(highlight.text)
    if (start === -1) continue
    const end = start + highlight.text.length
    for (let i = start; i < end; i++) {
      variantPerIndex[i] = highlight.variant
    }
  }

  const segments: Segment[] = []
  let segmentStart = 0
  for (let i = 1; i <= value.length; i++) {
    if (i === value.length || variantPerIndex[i] !== variantPerIndex[segmentStart]) {
      segments.push({ text: value.slice(segmentStart, i), variant: variantPerIndex[segmentStart] })
      segmentStart = i
    }
  }
  return segments
}

/**
 * Highlight paint only — must stay `display: inline` (never flex/block items)
 * so backgrounds wrap with glyphs. `box-decoration-break: clone` keeps the
 * marker wash continuous across soft line wraps (CSS-Tricks / highlighter pattern).
 */
const HIGHLIGHT_CLASSNAMES: Record<TextHighlightVariant, string> = {
  hover:
    "inline rounded-sm bg-suggestion-highlight/70 [box-decoration-break:clone] [-webkit-box-decoration-break:clone]",
  selected:
    "inline rounded-sm bg-suggestion-highlight shadow-[inset_0_-2px_0_0_hsl(var(--error))] [box-decoration-break:clone] [-webkit-box-decoration-break:clone]",
}

export type HighlightedTextareaProps = React.ComponentProps<"textarea"> & {
  /** Active highlight ranges to render for the current value. */
  highlights?: TextHighlight[]
}

/**
 * A native `<textarea>` with a non-interactive highlight overlay rendered
 * behind it, used to visually mark AI-suggestion excerpt spans inside
 * SOURCE/TARGET TEXT without altering native editing behavior — typing,
 * IME composition, caret placement, native text selection, and `onChange`
 * all pass through to the real `<textarea>` unchanged.
 *
 * Technique ("highlight-within-textarea", Coder's Block / CSS-Tricks):
 * the real textarea sits on top with transparent text/background (caret still
 * visible), while a backdrop layer behind it renders the visible text plus
 * inline highlight spans. Metrics (font, line-height, padding, border width,
 * white-space, scrollbar-gutter) are shared so wraps align; scrollTop/Left
 * are mirrored from the textarea.
 *
 * Important: do NOT put `display: flex` on the backdrop. Flex makes each
 * segment a stretched flex item (full backdrop height, content width) — the
 * "tall orange column" / character-stack bug. See
 * `openspec/changes/highlight-suggestion-text-spans/design.md`.
 */
export const HighlightedTextarea = React.forwardRef<HTMLTextAreaElement, HighlightedTextareaProps>(
  ({ className, highlights = [], value, onScroll, style, ...props }, forwardedRef) => {
    const internalRef = React.useRef<HTMLTextAreaElement | null>(null)
    const backdropRef = React.useRef<HTMLDivElement | null>(null)

    React.useImperativeHandle(forwardedRef, () => internalRef.current as HTMLTextAreaElement)

    const stringValue = typeof value === "string" ? value : value != null ? String(value) : ""

    const segments = React.useMemo(
      () => computeSegments(stringValue, highlights),
      [stringValue, highlights]
    )

    const handleScroll = React.useCallback(
      (e: React.UIEvent<HTMLTextAreaElement>) => {
        if (backdropRef.current) {
          backdropRef.current.scrollTop = e.currentTarget.scrollTop
          backdropRef.current.scrollLeft = e.currentTarget.scrollLeft
        }
        onScroll?.(e)
      },
      [onScroll]
    )

    // Box-model + typography shared by both layers. Intentionally omits
    // `flex` (vestigial on shadcn Textarea; catastrophic on a backdrop <div>
    // with inline segment children — see design.md Bug 1 / Bug 1b).
    const sharedMetricsClassName = cn(
      "min-h-[60px] w-full rounded-md border border-input px-3 py-2 text-base shadow-sm md:text-sm whitespace-pre-wrap break-words [scrollbar-gutter:stable]",
      className
    )

    return (
      <div className="relative">
        <div
          ref={backdropRef}
          aria-hidden="true"
          // Inline color avoids twMerge dropping `text-body-base` when a
          // `text-*` color utility is composed onto the same class string.
          style={{ color: "hsl(var(--on-surface))" }}
          className={cn(
            sharedMetricsClassName,
            // Block formatting context for inline segments; never flex/grid.
            "absolute inset-0 z-0 block overflow-auto pointer-events-none no-scrollbar"
          )}
        >
          {segments.map((segment, index) =>
            segment.variant ? (
              <span key={index} className={HIGHLIGHT_CLASSNAMES[segment.variant]}>
                {segment.text}
              </span>
            ) : (
              <span key={index}>{segment.text}</span>
            )
          )}
          {/* Textareas keep a trailing blank line for a final \\n; a block
              backdrop collapses it unless we mirror the extra newline. */}
          {stringValue.endsWith("\n") ? "\n" : null}
        </div>
        <textarea
          ref={internalRef}
          value={value}
          onScroll={handleScroll}
          className={cn(
            sharedMetricsClassName,
            "relative z-10 border-transparent bg-transparent shadow-none placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
          )}
          // Inline color (not `text-transparent`) so tailwind-merge cannot drop
          // caller font-size tokens like `text-body-base` — twMerge treats
          // `text-*` size and `text-*` color as one conflicting group by default.
          style={{
            ...style,
            color: "transparent",
            caretColor: "hsl(var(--on-surface))",
          }}
          {...props}
        />
      </div>
    )
  }
)
HighlightedTextarea.displayName = "HighlightedTextarea"
