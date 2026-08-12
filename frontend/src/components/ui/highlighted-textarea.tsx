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

const HIGHLIGHT_CLASSNAMES: Record<TextHighlightVariant, string> = {
  hover: "bg-suggestion-highlight/25 rounded-sm",
  selected: "bg-suggestion-highlight/45 border-b-2 border-suggestion-highlight rounded-sm",
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
 * Technique ("highlight-within-textarea"): the real textarea is rendered on
 * top with transparent text/background (so it still receives all input and
 * shows the native caret + selection), while a backdrop `<div>` behind it
 * renders the actual visible text plus `<mark>`-wrapped highlighted spans.
 * Both layers share the same className so glyph positions line up exactly.
 * Scroll position is mirrored from the textarea to the backdrop on scroll.
 *
 * See `openspec/changes/highlight-suggestion-text-spans/design.md`
 * (Decision 5) for the full rationale.
 */
export const HighlightedTextarea = React.forwardRef<HTMLTextAreaElement, HighlightedTextareaProps>(
  ({ className, highlights = [], value, onScroll, ...props }, forwardedRef) => {
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

    // Shared box-model/typography classes so the backdrop and textarea's
    // glyphs line up exactly. `className` (caller-supplied sizing/bg/border)
    // is included here so BOTH layers start from it, then each layer's
    // layer-specific classes below override what needs to differ (color,
    // interactivity) via tailwind-merge's last-wins conflict resolution.
    const sharedClassName = cn(
      "flex min-h-[60px] w-full rounded-md border border-input px-3 py-2 text-base shadow-sm md:text-sm whitespace-pre-wrap break-words",
      className
    )

    return (
      <div className="relative">
        <div
          ref={backdropRef}
          aria-hidden="true"
          className={cn(
            sharedClassName,
            "no-scrollbar absolute inset-0 z-0 overflow-auto text-on-surface pointer-events-none"
          )}
        >
          {segments.map((segment, index) =>
            segment.variant ? (
              <mark key={index} className={HIGHLIGHT_CLASSNAMES[segment.variant]}>
                {segment.text}
              </mark>
            ) : (
              <span key={index}>{segment.text}</span>
            )
          )}
        </div>
        <textarea
          ref={internalRef}
          value={value}
          onScroll={handleScroll}
          className={cn(
            sharedClassName,
            "relative z-10 border-transparent bg-transparent text-transparent shadow-none placeholder:text-muted-foreground caret-[hsl(var(--on-surface))] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
          )}
          {...props}
        />
      </div>
    )
  }
)
HighlightedTextarea.displayName = "HighlightedTextarea"
