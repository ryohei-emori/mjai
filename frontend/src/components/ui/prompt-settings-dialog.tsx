"use client"

import * as React from "react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Textarea } from "@/components/ui/textarea"
import { settingsAPI, type PromptSettingsResponse } from "@/app/api"
import { PROMPT_COMPOSITION_STEPS } from "@/lib/promptComposition"

/**
 * Editor for the shared AI-correction prompt (top-bar settings).
 *
 * The prompt is one global record: everyone sees and edits the same text, and it
 * lives in Postgres so it survives logout instead of being re-entered per
 * session. Only the rules body is editable — the JSON output contract is always
 * appended by code on both the cloud and offline paths, so a bad edit can lower
 * critique quality but cannot break parsing.
 *
 * Loads on open (not on mount) so a user who never opens settings pays nothing,
 * and so reopening always shows what is actually stored rather than stale text.
 *
 * Copy is English because the people who tune critique quality read the prompt
 * itself, which is Chinese, and were reading Japanese chrome around it.
 */
export const PROMPT_MAX_LENGTH = 20000

export type PromptSettingsDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  /** Feedback channel; the caller owns the toast implementation. */
  onSaved?: (message: string) => void
}

export function PromptSettingsDialog({
  open,
  onOpenChange,
  onSaved,
}: PromptSettingsDialogProps) {
  const [settings, setSettings] = React.useState<PromptSettingsResponse | null>(null)
  const [draft, setDraft] = React.useState("")
  const [isLoading, setIsLoading] = React.useState(false)
  const [isSaving, setIsSaving] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)
  const [confirmingReset, setConfirmingReset] = React.useState(false)

  React.useEffect(() => {
    if (!open) return
    let cancelled = false
    setIsLoading(true)
    setError(null)
    setConfirmingReset(false)
    settingsAPI
      .getPrompt()
      .then((loaded) => {
        if (cancelled) return
        setSettings(loaded)
        setDraft(loaded.systemPrompt)
      })
      .catch((e: unknown) => {
        if (cancelled) return
        setError(e instanceof Error ? e.message : "Failed to load the prompt.")
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [open])

  const trimmed = draft.trim()
  const isEmpty = trimmed.length === 0
  const isTooLong = trimmed.length > PROMPT_MAX_LENGTH
  const isUnchanged = settings ? draft === settings.systemPrompt : true
  const validationMessage = isEmpty
    ? "The prompt cannot be empty."
    : isTooLong
      ? `Keep the prompt within ${PROMPT_MAX_LENGTH.toLocaleString()} characters (currently ${trimmed.length.toLocaleString()}).`
      : null
  // A failed load leaves the editor empty, which would otherwise report
  // "cannot be empty" and hide the reason the prompt never arrived.
  const message = error || validationMessage
  const canSave = !isLoading && !isSaving && !isUnchanged && !validationMessage

  const handleSave = async () => {
    setIsSaving(true)
    setError(null)
    try {
      const saved = await settingsAPI.updatePrompt(trimmed)
      setSettings(saved)
      setDraft(saved.systemPrompt)
      onSaved?.("System prompt saved. It applies from the next generation.")
      onOpenChange(false)
    } catch (e: unknown) {
      // Keep the edited text so a failed save never costs the user their work.
      setError(e instanceof Error ? e.message : "Failed to save the prompt.")
    } finally {
      setIsSaving(false)
    }
  }

  const handleReset = async () => {
    if (!confirmingReset) {
      setConfirmingReset(true)
      return
    }
    setIsSaving(true)
    setError(null)
    try {
      const reset = await settingsAPI.resetPrompt()
      setSettings(reset)
      setDraft(reset.systemPrompt)
      setConfirmingReset(false)
      onSaved?.("Reset to the default prompt.")
    } catch (e: unknown) {
      setError(
        e instanceof Error ? e.message : "Failed to reset to the default prompt.",
      )
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="wide" aria-describedby="prompt-settings-description">
        <DialogHeader>
          <div className="flex items-center gap-2 flex-wrap">
            <DialogTitle>System Prompt</DialogTitle>
            {settings && (
              <Badge
                variant={settings.isCustomized ? "default" : "secondary"}
                className="text-xs"
              >
                {settings.isCustomized ? "Custom" : "Default"}
              </Badge>
            )}
          </div>
          <DialogDescription id="prompt-settings-description">
            System prompt for AI suggestions. Shared across all users and
            sessions, so it survives signing out. The JSON output format is
            always appended automatically — you do not need to write it here.
          </DialogDescription>
        </DialogHeader>

        {settings?.isCustomized && (settings.updatedBy || settings.updatedAt) && (
          <p className="text-metadata text-on-surface-variant">
            Last updated by {settings.updatedBy || "unknown user"}
            {settings.updatedAt
              ? ` / ${new Date(settings.updatedAt).toLocaleString()}`
              : ""}
          </p>
        )}

        {/* Answers "where does EXEMPLAR TEXT go?" — the editor shows one field,
            while what reaches the model is this field plus five other pieces.
            The order comes from PROMPT_COMPOSITION_STEPS, which the prompt
            builders are tested against, so this cannot quietly go stale. */}
        <details className="rounded-lg border border-outline-variant bg-surface-container-low px-3 py-2">
          <summary className="cursor-pointer text-body-sm text-on-surface">
            How your prompt is assembled
          </summary>
          <ol className="mt-2 space-y-1.5">
            {PROMPT_COMPOSITION_STEPS.map((step, index) => (
              <li key={step.id} className="text-metadata text-on-surface-variant">
                <span className="font-medium text-on-surface">
                  {index + 1}. {step.label}
                </span>
                {step.conditional && (
                  <span className="ml-1 text-on-surface-variant">
                    (only when EXEMPLAR TEXT is filled in)
                  </span>
                )}
                <span className="block">{step.detail}</span>
              </li>
            ))}
          </ol>
        </details>

        <Textarea
          aria-label="System prompt"
          value={draft}
          onChange={(e) => {
            setDraft(e.target.value)
            if (error) setError(null)
          }}
          disabled={isLoading || isSaving}
          spellCheck={false}
          // Takes whatever height the dialog has left rather than claiming a
          // share of the viewport: `45vh`/`55vh` ignored the header, footer and
          // counters above and below it, which on a phone with the keyboard open
          // pushed the save button out of the dialog entirely. The floor is what
          // it may not shrink past, so the tall one is behind `sm:` — raising it
          // unconditionally would put the footer back below the fold.
          className="flex-1 min-h-[12rem] sm:min-h-[24rem] overflow-y-auto font-mono text-body-sm leading-relaxed bg-surface-container border-outline-variant"
        />

        <p className="text-metadata text-on-surface-variant">
          {isLoading
            ? "Loading..."
            : `${trimmed.length.toLocaleString()} / ${PROMPT_MAX_LENGTH.toLocaleString()} characters`}
        </p>

        {message && (
          <p role="alert" className="text-body-sm text-red-600">
            {message}
          </p>
        )}

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={handleReset}
            disabled={isLoading || isSaving || (!settings?.isCustomized && !confirmingReset)}
          >
            {confirmingReset ? "Confirm Reset" : "Reset to Default"}
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isSaving}
          >
            Cancel
          </Button>
          <Button type="button" onClick={handleSave} disabled={!canSave}>
            {isSaving ? "Saving..." : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
