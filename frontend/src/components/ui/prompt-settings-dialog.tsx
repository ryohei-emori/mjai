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

/**
 * Editor for the shared AI-correction prompt (top-bar settings).
 *
 * The prompt is one global record: everyone sees and edits the same text, and it
 * lives in Postgres so it survives logout instead of being re-entered per
 * session. Only the rules body is editable — the backend always appends the JSON
 * output contract, so a bad edit can lower critique quality but cannot break
 * parsing.
 *
 * Loads on open (not on mount) so a user who never opens settings pays nothing,
 * and so reopening always shows what is actually stored rather than stale text.
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
        setError(e instanceof Error ? e.message : "プロンプトの読み込みに失敗しました")
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
    ? "プロンプトを空にはできません。"
    : isTooLong
      ? `${PROMPT_MAX_LENGTH.toLocaleString()}文字以内にしてください（現在 ${trimmed.length.toLocaleString()}文字）。`
      : null
  // A failed load leaves the editor empty, which would otherwise report
  // "空にはできません" and hide the reason the prompt never arrived.
  const message = error || validationMessage
  const canSave = !isLoading && !isSaving && !isUnchanged && !validationMessage

  const handleSave = async () => {
    setIsSaving(true)
    setError(null)
    try {
      const saved = await settingsAPI.updatePrompt(trimmed)
      setSettings(saved)
      setDraft(saved.systemPrompt)
      onSaved?.("添削プロンプトを保存しました。次の生成から適用されます。")
      onOpenChange(false)
    } catch (e: unknown) {
      // Keep the edited text so a failed save never costs the user their work.
      setError(e instanceof Error ? e.message : "プロンプトの保存に失敗しました")
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
      onSaved?.("既定のプロンプトに戻しました。")
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "既定に戻せませんでした")
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent aria-describedby="prompt-settings-description">
        <DialogHeader>
          <div className="flex items-center gap-2 flex-wrap">
            <DialogTitle>添削プロンプト</DialogTitle>
            {settings && (
              <Badge
                variant={settings.isCustomized ? "default" : "secondary"}
                className="text-xs"
              >
                {settings.isCustomized ? "カスタム" : "既定"}
              </Badge>
            )}
          </div>
          <DialogDescription id="prompt-settings-description">
            AI提案の指示文です。全ユーザー共通で保存され、ログインし直しても入力し直す必要はありません。
            出力形式（JSON）の指定はシステム側で常に付加されるため、ここには書く必要がありません。
          </DialogDescription>
        </DialogHeader>

        {settings?.isCustomized && (settings.updatedBy || settings.updatedAt) && (
          <p className="text-metadata text-on-surface-variant">
            最終更新: {settings.updatedBy || "不明なユーザー"}
            {settings.updatedAt
              ? ` / ${new Date(settings.updatedAt).toLocaleString()}`
              : ""}
          </p>
        )}

        <Textarea
          aria-label="添削プロンプト"
          value={draft}
          onChange={(e) => {
            setDraft(e.target.value)
            if (error) setError(null)
          }}
          disabled={isLoading || isSaving}
          spellCheck={false}
          className="min-h-[45vh] max-h-[55vh] overflow-y-auto font-mono text-body-sm leading-relaxed bg-surface-container border-outline-variant"
        />

        <div className="flex items-center justify-between gap-2 flex-wrap">
          <p className="text-metadata text-on-surface-variant">
            {isLoading
              ? "読み込み中..."
              : `${trimmed.length.toLocaleString()} / ${PROMPT_MAX_LENGTH.toLocaleString()} 文字`}
          </p>
          <p className="text-metadata text-on-surface-variant">
            オフラインモード（WebLLM）は端末内の専用プロンプトを使うため、この設定は適用されません。
          </p>
        </div>

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
            {confirmingReset ? "本当に既定に戻す" : "既定に戻す"}
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isSaving}
          >
            キャンセル
          </Button>
          <Button type="button" onClick={handleSave} disabled={!canSave}>
            {isSaving ? "保存中..." : "保存"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
