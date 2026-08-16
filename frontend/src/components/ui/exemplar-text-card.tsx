"use client"

import * as React from "react"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"

/**
 * EXEMPLAR TEXT (模範回答訳文) card for the correction workspace.
 *
 * Optional input: a known-good translation of the SOURCE TEXT that the backend
 * and WebLLM prompts use purely to calibrate expected meaning and register.
 * Never required for generation — the "Generate AI Suggestions" control stays
 * governed by TARGET/SOURCE text alone.
 *
 * Extracted into its own component rather than inlined next to the SOURCE and
 * TARGET cards in `page.tsx` because this card is collapsible
 * (`floating-session-pane-and-collapsible-panels`), and a collapse wrapper is
 * far easier to add around a self-contained component.
 *
 * Collapsed by default: the exemplar is fixed per exercise and rarely needs
 * re-reading, so keeping its textarea permanently expanded only pushed TARGET
 * TEXT and the generate control down. The textarea is conditionally rendered
 * rather than CSS-hidden, matching every other disclosure in this codebase and
 * keeping it out of the tab order while collapsed. `open` is controlled by the
 * caller, which owns its `localStorage` persistence.
 *
 * Uses a plain `Textarea` rather than `HighlightedTextarea`: suggestion spans
 * point at SOURCE and TARGET excerpts, never at the exemplar.
 */
export type ExemplarTextCardProps = {
  value: string
  onChange: (value: string) => void
  onCopy?: (value: string) => void
  open?: boolean
  onOpenChange?: (open: boolean) => void
  className?: string
}

const CONTENT_ID = "exemplar-text-card-content"

export function ExemplarTextCard({
  value,
  onChange,
  onCopy,
  open = false,
  onOpenChange,
  className,
}: ExemplarTextCardProps) {
  const hasValue = value.trim().length > 0

  return (
    <Card
      className={`bg-surface border border-outline-variant shadow-none${
        className ? ` ${className}` : ""
      }`}
      data-testid="exemplar-text-card"
    >
      <CardHeader className={open ? "pb-3" : undefined}>
        <div className="flex items-center justify-between gap-2">
          <button
            type="button"
            onClick={() => onOpenChange?.(!open)}
            aria-expanded={open}
            aria-controls={CONTENT_ID}
            className="flex flex-1 min-w-0 items-center gap-2 text-left rounded focus-visible:ring-2 focus-visible:ring-md3-primary"
          >
            <span
              className={`material-symbols-outlined md-18 text-on-surface-variant transition-transform ${
                open ? "rotate-180" : ""
              }`}
            >
              expand_more
            </span>
            <CardTitle className="text-label-caps tracking-wider text-on-surface-variant uppercase">
              EXEMPLAR TEXT (模範回答訳文)
              <span className="ml-2 normal-case tracking-normal text-metadata text-on-surface-variant/70">
                任意
              </span>
            </CardTitle>
            {/* 閉じている間に入力内容が黙って隠れないよう、入力済みであることを
                ヘッダーで示す（文字数まで出すので中身の見当もつく）。 */}
            {!open && hasValue && (
              <>
                <Badge className="bg-session-complete text-white text-xs font-medium shrink-0">
                  入力あり
                </Badge>
                <span className="normal-case tracking-normal text-metadata text-on-surface-variant shrink-0">
                  {value.length}文字
                </span>
              </>
            )}
          </button>
          {onCopy && (
            <button
              onClick={() => value && onCopy(value)}
              className="p-1.5 rounded hover:bg-surface-container transition-colors shrink-0 touch-target"
              title="コピー"
              aria-label="模範回答訳文をコピー"
            >
              <span className="material-symbols-outlined md-18 text-on-surface-variant">
                content_copy
              </span>
            </button>
          )}
        </div>
      </CardHeader>
      {open && (
        <CardContent id={CONTENT_ID}>
          <Textarea
            placeholder="模範回答の訳文があれば貼り付けてください（任意）。AIは対比の参考にのみ使い、丸写しの添削はしません..."
            value={value}
            onChange={(e) => onChange(e.target.value)}
            className="min-h-[140px] text-body-base leading-relaxed bg-surface-container border-outline-variant"
          />
        </CardContent>
      )}
    </Card>
  )
}
