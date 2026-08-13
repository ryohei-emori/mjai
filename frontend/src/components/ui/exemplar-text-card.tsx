"use client"

import * as React from "react"

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
 * TARGET cards in `page.tsx` because this card is slated to become collapsible
 * (`floating-session-pane-and-collapsible-panels`), and a collapse wrapper is
 * far easier to add around a self-contained component.
 *
 * Uses a plain `Textarea` rather than `HighlightedTextarea`: suggestion spans
 * point at SOURCE and TARGET excerpts, never at the exemplar.
 */
export type ExemplarTextCardProps = {
  value: string
  onChange: (value: string) => void
  onCopy?: (value: string) => void
  className?: string
}

export function ExemplarTextCard({
  value,
  onChange,
  onCopy,
  className,
}: ExemplarTextCardProps) {
  return (
    <Card
      className={`bg-surface border border-outline-variant shadow-none${
        className ? ` ${className}` : ""
      }`}
      data-testid="exemplar-text-card"
    >
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-label-caps tracking-wider text-on-surface-variant uppercase">
            EXEMPLAR TEXT (模範回答訳文)
            <span className="ml-2 normal-case tracking-normal text-metadata text-on-surface-variant/70">
              任意
            </span>
          </CardTitle>
          {onCopy && (
            <button
              onClick={() => value && onCopy(value)}
              className="p-1.5 rounded hover:bg-surface-container transition-colors"
              title="コピー"
            >
              <span className="material-symbols-outlined md-18 text-on-surface-variant">
                content_copy
              </span>
            </button>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <Textarea
          placeholder="模範回答の訳文があれば貼り付けてください（任意）。AIは対比の参考にのみ使い、丸写しの添削はしません..."
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="min-h-[140px] text-body-base leading-relaxed bg-surface-container border-outline-variant"
        />
      </CardContent>
    </Card>
  )
}
