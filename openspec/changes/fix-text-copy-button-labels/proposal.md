## Why

The copy button in the SOURCE TEXT card copies `currentSession.originalText` (原文) but shows a toast claiming "修正内容がクリップボードにコピーされました" (corrected content copied) — this is factually wrong for that button, because raw source text is not "修正内容" (corrected/final content). Separately, the TARGET TEXT card header has two decorative, non-functional Material Symbols icons (`format_bold`, `format_italic`) left over from an early mockup — they have no `onClick` and do nothing, when the user clearly expects a TARGET-text copy button there instead, mirroring the SOURCE TEXT card.

## What Changes

- `copyToClipboard()` gains an optional `description` parameter so each call site can supply an accurate, content-specific toast description instead of a single hardcoded "修正内容が..." string used everywhere.
- The SOURCE TEXT copy button's toast now reads "原文がクリップボードにコピーされました" instead of the misleading "修正内容が...".
- The AI-suggestion-card copy button's toast now reads "提案内容がクリップボードにコピーされました" (it copies a proposal's excerpt + reason, not the final corrected content).
- The `saveCorrections()` combined-comment copy site keeps its existing, accurate "修正内容がクリップボードにコピーされました" wording (it genuinely copies the finalized corrected content).
- The two decorative `format_bold`/`format_italic` spans in the TARGET TEXT card header are replaced with a single functional copy button, structurally identical to the SOURCE TEXT card's copy button, wired to `copyToClipboard(currentSession.targetText, "添削対象テキストがクリップボードにコピーされました")`, guarded against copying empty text.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `correction-workspace-ui`: The "Clipboard Copy Feedback" requirement is strengthened so the success-toast description accurately reflects what was actually copied (source text, target text, a proposal, or finalized corrected content) instead of always claiming "修正内容". The "Correction Input Form" requirement gains a TARGET TEXT copy-button scenario mirroring the existing SOURCE TEXT copy-button behavior.

## Impact

- **Frontend code**: `frontend/src/app/page.tsx` only — `copyToClipboard()` signature (new optional parameter), its four call sites' arguments, and the TARGET TEXT card header markup (decorative spans → functional button).
- **No backend changes.**
- **No database schema changes.**
- **No design-token changes**: the new TARGET TEXT copy button reuses the SOURCE TEXT copy button's existing classes verbatim, so `docs/UI-DESIGN.md` needs no update.
