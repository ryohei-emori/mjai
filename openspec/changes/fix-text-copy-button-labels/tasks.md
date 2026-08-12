## 1. `copyToClipboard` helper

- [x] 1.1 Add an optional `description` parameter to `copyToClipboard(text: string, description?: string)` with an accurate, content-neutral default (e.g. "クリップボードにコピーしました"), and use it in the success toast instead of the hardcoded "修正内容が..." string

## 2. Fix toast wording at existing call sites

- [x] 2.1 SOURCE TEXT card copy button: pass "原文がクリップボードにコピーされました"
- [x] 2.2 AI-suggestion card copy button: pass "提案内容がクリップボードにコピーされました"
- [x] 2.3 `saveCorrections()` combined-comment copy call: pass "修正内容がクリップボードにコピーされました" explicitly (keep existing accurate wording)

## 3. TARGET TEXT card copy button

- [x] 3.1 Remove the two decorative `format_bold`/`format_italic` `<span>` elements (and their now-unnecessary wrapping `<div className="flex items-center gap-1">`) from the TARGET TEXT card header
- [x] 3.2 Add a functional copy button in their place, structurally identical to the SOURCE TEXT card's copy button (same classes, `content_copy` icon, `title="コピー"`), wired to `copyToClipboard(currentSession.targetText, "添削対象テキストがクリップボードにコピーされました")`, guarded by `currentSession?.targetText &&` so it no-ops on empty text

## 4. Verification

- [x] 4.1 Run `npm run lint` in `frontend/` and confirm no new errors
- [x] 4.2 Run `npm run build` in `frontend/` and confirm it succeeds
- [x] 4.3 Re-read the edited sections of `frontend/src/app/page.tsx` to confirm no collision with the concurrent `persist-source-target-text-input` change's edits to `onChange`/session-loading logic
