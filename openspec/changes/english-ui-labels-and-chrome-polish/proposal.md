## Why

The workspace chrome is bilingual by accident rather than by design: card headings, nav tabs and panel titles are English (`SOURCE TEXT`, `Job Queue`, `History`), while the controls between them are still Japanese (`オフラインモード（WebLLM）`, `確認待ちの完了ジョブ`, `選択済み: 0/3+`, `編集` / `添削案`). The user reads the correction content in Japanese and Chinese; the chrome that frames it should be one language, and the codebase already chose English for it.

Three chrome defects surfaced with the same review:

- **Scrollbars render black** on the session screen. `globals.css` sets `color-scheme: dark` under `prefers-color-scheme: dark`, but the app has no dark theme wired up (`.dark` is never applied), so on an OS in dark mode every native scrollbar is painted for a dark UI inside a light one. That is outside every token in `docs/UI-DESIGN.md`.
- **Non-interactive readouts darken on hover.** The `LATEST` / `AVG` timing badges, `Saved: N` and the selection counter all go near-black under the cursor, because shadcn's `badgeVariants` carries `hover:bg-primary/80` and `--primary` is `0 0% 9%` — a legacy shadcn token, not an MD3 one. Nothing in this app makes a `Badge` clickable, so the hover state promises an interaction that does not exist.
- **A redundant provider badge.** `クラウドAPI` / `ローカルAI` next to the offline-mode checkbox repeats what the job card's `API` / `WebLLM` badge and the model-provenance caption already say.

Finally the `New Session` action reads lighter than its prominence warrants, at the button component's default `text-sm`.

## What Changes

- Translate the remaining Japanese chrome on the session screen to English, matching the existing uppercase/`text-label-caps` tone: pane switch (`編集` / `添削案` → `TEXT` / `SUGGESTIONS`), notifications panel subtitle and empty state, job status and provider badges, `選択済み` counter, session `作成日` line, offline-mode label, exemplar-card `任意` marker, search/placeholder text, `title` / `aria-label` attributes and toast copy. AI-generated Chinese critique text and user-entered Japanese text are untouched.
- Set `color-scheme: light` unconditionally and give the workspace scroll regions a token-based scrollbar (`--outline-variant` thumb, `--outline` on hover), matching the Job Queue carousel's existing rail without changing its always-visible behaviour.
- Remove the `hover:bg-*` states from `Badge`, making it a display element again.
- Remove the `クラウドAPI` / `ローカルAI` badge.
- Raise `New Session` to `text-body-base` at `font-semibold`, both existing typography-scale values.
- Update `docs/UI-DESIGN.md` for the token-based scrollbar, the non-interactive badge, and the button weight.

Timestamps rendered with `toLocaleString()` follow the browser locale and are left alone: the surrounding label becomes `Created:`, but forcing `en-US` on a user whose browser is Japanese would make the date harder to read, not more consistent.

## Capabilities

### New Capabilities

None — this changes how existing workspace behaviour is presented, not what it does.

### Modified Capabilities

- `correction-workspace-ui`: the language of the workspace chrome becomes a stated requirement rather than an accident; scroll regions and non-interactive readouts get required visual behaviour; the provider badge next to the offline toggle is removed.

## Impact

- `frontend/src/app/page.tsx` — chrome copy, pane-switch labels, provider badge removal, New Session weight, scroll-region class
- `frontend/src/app/globals.css` — `color-scheme`, new `.token-scrollbar` utility
- `frontend/src/components/ui/badge.tsx` — hover states removed
- `frontend/src/components/ui/scroll-area.tsx` — thumb moves from `--border` to `--outline-variant`
- `frontend/src/components/ui/exemplar-text-card.tsx` — header copy
- `frontend/src/components/ui/job-queue-carousel.tsx` — arrow labels and hint text
- `frontend/src/app/__tests__/apiError.test.tsx`, `frontend/src/components/ui/__tests__/*` — assertions that name Japanese labels
- `docs/UI-DESIGN.md`
- Out of scope: `backend/`, `frontend/src/lib/webllm/prompts/*`, the prompt-settings dialog, and any string sent to the API or persisted (`instructionPrompt`, parser sentinel text)
