## Why

The correction prompt is the product. Today it lives only in Python (`backend/app/llm/prompts.py`), so the person who actually judges critique quality cannot change a single rule without a code change and a deploy — while the reported session shows the current rules failing in ways a prompt edit could fix immediately:

- The "corrected form" was handed back **in Chinese** for a Japanese target (`改为“对比睡眠数据”`, `改为“理论上”`, `“体型や脳容量”也可以改为“体型、脑容量等”`), so the suggestion is unusable as a correction: 「理论上」 is not Japanese.
- One item critiqued the **Chinese source sentence** (`文化也完成了逐渐独特的进化` → `实现`) instead of the Japanese target, i.e. it corrected the wrong text entirely.
- Several items were **near-synonym preferences, not errors** (比較⇄対比, 研究者⇄学者, 完成⇄实现) — as the user put it, 「本質的な間違いじゃない」.
- A recommended form produced **ungrammatical Japanese** (必要 → 需要 yields 「睡眠が需要だ」), because Chinese collocation was transplanted into Japanese without checking the result.
- Framing was lexical substitution ("word A is more natural than word B") rather than translation critique: whether a Japanese reader receives the source's meaning.

There is also no way to tell **which model** produced any of those critiques. Both Gemini and Groq rotate models per request (`ALLOWED_GEMINI_MODELS`, `ALLOWED_GROQ_MODELS`) and the winning provider is only visible in serverless logs, never in the response, the UI, or the database. So quality feedback cannot be attributed, and a bad model cannot be excluded on evidence.

## What Changes

- **Add a settings dialog** opened from the existing (currently disabled) gear button at the top-right of the top bar, containing the AI correction system prompt as editable text, pre-filled with the prompt the system uses today.
- **Persist that prompt in Supabase Postgres as one shared, global record**, not per user and not in `localStorage`: any signed-in (allow-listed) user sees and edits the same prompt, and it survives logout, browser change, and redeploy without re-entry.
- **Apply the saved prompt to cloud suggestion generation**, replacing the built-in default when a custom prompt exists, with a reset-to-default action and a code-owned JSON output contract that no edit can delete (so a bad edit degrades critique quality but cannot break the response format).
- **Return the winning provider and model id from `POST /api/suggestions`** and persist them on the correction history row, so every generated suggestion set carries its provenance in the shared database.
- **Show an unobtrusive "<model> used" caption** next to the AI suggestion results (and on a restored history round), sized and coloured as metadata so it never competes with the suggestions themselves.
- **Fix the default prompt's critique rules and few-shot example** so recommended forms are always Japanese, only the target text is critiqued, near-synonym preferences are not reported as faults, a recommended form must be checked for collocational validity in its sentence, and reasons are framed as cross-language meaning transfer.
- **Add a mechanical guard** that treats "recommended form written in Chinese" as an unusable response and retries within the existing attempt budget, the same way non-Chinese explanation prose is already retried.

Not included: per-user prompt variants, prompt version history / rollback beyond reset-to-default, applying the custom prompt to the offline WebLLM path, and editing the few-shot example from the UI.

## Capabilities

### New Capabilities

- `prompt-settings`: a single shared, DB-persisted AI correction prompt — read/update/reset API, validation, default seeding, last-edited attribution, and how a saved prompt reaches generation.

### Modified Capabilities

- `ai-suggestions`: the effective system prompt SHALL come from the stored prompt when one exists (default otherwise) with a code-owned output contract; `POST /api/suggestions` SHALL report the winning provider and model; critique rules gain target-language, scope, substantiveness, collocation-validity and meaning-transfer requirements, plus a retry trigger for Chinese recommended forms and a matching few-shot exemplar.
- `correction-workspace-ui`: the top-bar settings button SHALL open a prompt settings dialog (load / edit / save / reset / attribution / validation errors), and the workspace SHALL display the model used for the displayed suggestion set as metadata-level text.
- `correction-history`: correction history rows SHALL carry the LLM provider and model that generated their suggestions, accepted on create, returned on read, and shown by history-restoring surfaces.

## Impact

- **Database**: new `app_settings` key/value table; new `llm_provider` / `llm_model` columns on `correction_histories`. Two new migrations under `backend/supabase/migrations/`, applied to the shared Supabase project before deploy (same shared-DB caveat as `005_pending_suggestion_histories.sql`).
- **Backend**: `backend/app/llm/prompts.py` (split editable rule body from the code-owned output contract; rewrite critique rules + few-shot), `suggestions.py` (thread prompt override, report provider/model, new retry trigger), `parser.py` (Chinese-recommendation heuristic), `gemini_provider.py` / `groq_provider.py` / `cloudflare_provider.py` (report the model actually used), `main.py` (settings routes, provenance in the suggestions response, provenance fields on histories), `db_helper.py` (settings CRUD, history provenance columns).
- **Frontend**: `frontend/src/app/page.tsx` (enable the gear button, mount the dialog, capture and display provenance, pass it to `createHistory`), a new settings dialog component plus a `Dialog` primitive under `frontend/src/components/ui/` (only `sheet` exists today), and `frontend/src/app/api.ts` (`settingsAPI`, provenance fields on the suggestions/history types).
- **Latency budget**: one extra short-timeout DB read per generation, inside the existing 55s wall-clock budget; a custom prompt may be longer than the default, which raises prompt tokens.
- **Docs**: `AGENTS.md` (editable-prompt behavior, new endpoints/table/columns, response fields), `docs/SYSTEM-DESIGN.md` (data model, API, prompt flow), `docs/UI-DESIGN.md` (settings dialog + metadata caption).
- **API compatibility**: additive only — new response fields, new optional history fields, new endpoints; clients that ignore them keep working.
