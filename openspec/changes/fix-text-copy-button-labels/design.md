## Context

See `proposal.md` for motivation. This is a small, self-contained UI/copy fix confined to `frontend/src/app/page.tsx`. A `design.md` is included per this repo's schema requirement (`tasks` depends on both `specs` and `design`), even though the technical decisions are minor.

Note: a separate, unrelated background change (`persist-source-target-text-input`) is concurrently editing the same file's `updateCurrentSession({ originalText/targetText: ... })` onChange handlers and session-loading logic. This change does not touch those handlers or `loadSessions()` — it only touches the `copyToClipboard` helper, its call sites, and the TARGET TEXT card header's action-icon markup.

## Goals / Non-Goals

**Goals:**
- Make every `copyToClipboard()` call site's toast description accurately describe what was copied.
- Give the TARGET TEXT card header a working copy button, structurally identical to the SOURCE TEXT card's.

**Non-Goals:**
- Changing the SOURCE/TARGET textarea `onChange` handlers, session state shape, or draft-persistence logic (owned by the concurrent `persist-source-target-text-input` change).
- Deduplicating the two back-to-back toasts that already appear during `saveCorrections()` (the generic `copyToClipboard` toast followed by a flow-specific "保存完了"/"確認完了" toast) — that's a pre-existing UX quirk, out of scope here.
- Any visual/styling redesign beyond swapping decorative spans for a functional button using the SOURCE TEXT card's existing classes verbatim.

## Decisions

### 1. Thread an optional `description` parameter through `copyToClipboard` rather than removing the shared helper

**Choice**: `copyToClipboard(text: string, description: string = "クリップボードにコピーしました")`. Every existing call site is updated to pass an explicit, accurate description; the default only matters if a future call site forgets to pass one, and is itself accurate (makes no claim about content type).

**Alternative considered**: Inline separate `navigator.clipboard.writeText` + `toast` calls at each site instead of a shared helper. Rejected — it would duplicate the try/catch/error-toast logic across four call sites for no benefit; threading a parameter is the minimal diff.

### 2. TARGET TEXT copy button reuses the SOURCE TEXT copy button's JSX structure and classes verbatim

**Choice**: Copy the `<button>` element's structure (`p-1.5 rounded hover:bg-surface-container transition-colors`, `title="コピー"`, `content_copy` icon at `md-18`) from the SOURCE TEXT card, changing only the `onClick` target (`currentSession?.targetText && copyToClipboard(currentSession.targetText, ...)`). This satisfies the requirement that it be "structurally identical" and avoids introducing any new Tailwind classes or design tokens.

**Alternative considered**: Wrap the button in the existing `<div className="flex items-center gap-1">` that previously held the two decorative spans. Since there's now only one child, the wrapping `<div>` is no longer structurally necessary, but keeping it is a smaller diff than removing it and risking a layout shift; it also matches the SOURCE TEXT card's header, which wraps its single copy button directly in the `flex items-center justify-between` row without an extra inner div. To mirror the SOURCE TEXT card exactly, the inner `<div className="flex items-center gap-1">` wrapper is removed and the button becomes a direct sibling of `CardTitle`, matching the SOURCE TEXT card's DOM shape.

## Risks / Trade-offs

- [Risk] Concurrent edits from the `persist-source-target-text-input` background agent to the same file could cause a `StrReplace` old-string mismatch. → Mitigation: use small, tightly-scoped `StrReplace` calls anchored on unique surrounding text (function signature, specific `onClick` lines) rather than large block replacements; re-read the file fresh before retrying on any mismatch.
- [Risk] Removing the decorative icons could be mistaken for a regression by someone expecting bold/italic text formatting. → Mitigation: this proposal's Why section documents that those icons were never wired to any handler (dead mockup leftovers), not a removed working feature.
