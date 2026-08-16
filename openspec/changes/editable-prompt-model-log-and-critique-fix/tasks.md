## 1. Database schema

- [x] 1.1 Add `backend/supabase/migrations/006_app_settings.sql`: `app_settings(setting_key TEXT PRIMARY KEY, setting_value TEXT NOT NULL, updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_by TEXT)` with `CREATE TABLE IF NOT EXISTS`, RLS enabled and the same permissive policy name as existing tables, plus `COMMENT ON TABLE/COLUMN` describing the `correction_system_prompt` key
- [x] 1.2 Add `backend/supabase/migrations/007_history_llm_provenance.sql`: `ADD COLUMN IF NOT EXISTS llm_provider TEXT` and `llm_model TEXT` on `correction_histories`, with column comments distinguishing them from the existing transport-level `provider`
- [x] 1.3 Apply both migrations to the shared Supabase project (they are additive, so current production code keeps working) and note in the change that this precedes deploy — **applied 2026-08-16 via `.github/workflows/apply-migrations.yml` (run 31936101275): remote history was empty, 001-005 recorded with `migration repair`, 006/007 pushed, and `app_settings` / `llm_provider` / `llm_model` verified with `psql`. See `design.md` Validation Results**

## 2. Backend prompt settings store and API

- [x] 2.1 Add settings CRUD to `backend/app/db_helper.py`: read one setting by key, upsert with `updated_at`/`updated_by`, delete by key — all through the existing `get_db()` context manager and camelCase-mapped returns
- [x] 2.2 Add a prompt-settings module (or main.py handlers) exposing `GET /settings/prompt` returning `{ systemPrompt, defaultSystemPrompt, isCustomized, updatedAt, updatedBy }`, with attribution fields absent/null when not customized
- [x] 2.3 Add `PUT /settings/prompt` accepting `{ systemPrompt }`: trim-empty → 400 with a reason, over 20,000 chars → 400 stating the limit, otherwise upsert with `updated_by` taken from the authenticated JWT's email and return the read shape
- [x] 2.4 Add `DELETE /settings/prompt` (reset) that deletes the row, is idempotent when no row exists, and returns the read shape with `isCustomized: false`
- [x] 2.5 Register the routes on the existing authenticated `router` (so they are served at both `/settings/...` and `/api/settings/...` and inherit JWT + allow-list enforcement)
- [x] 2.6 Add a short-timeout read helper used by the generation path that returns the stored prompt or `None`, never raising, and logs a warning on timeout/error

## 3. Backend prompt composition

- [x] 3.1 Split `backend/app/llm/prompts.py` into `SYSTEM_PROMPT_BODY` (editable rules) and `OUTPUT_CONTRACT` (JSON-only instruction + `格式：` schema line), keeping `SYSTEM_PROMPT = BODY + OUTPUT_CONTRACT` byte-identical to today's value
- [x] 3.2 Extend `build_system_prompt(exemplar_translation=None, override=None)` to compose `(override or BODY) [+ EXEMPLAR_REFERENCE_RULES when exemplar] + OUTPUT_CONTRACT`, and thread `override` through `build_messages()`
- [x] 3.3 Thread `system_prompt_override` from the `/suggestions` handler through `generate_suggestions()` into `build_messages()`, reading the stored prompt via 2.6 and falling back to the default on failure
- [x] 3.4 Confirm the wall-clock deadline is established before the settings read so the lookup is inside the existing 55s budget

## 4. Backend provider/model provenance

- [x] 4.1 Add a `ProviderOutput` value type (`text`, `model`) and return it from `call_gemini_with_rotation()` and `call_groq_with_rotation()`, reporting the model that actually produced the content (including after in-provider retry or credential rotation)
- [x] 4.2 Update `backend/app/llm/suggestions.py` call sites for the new return type, and pair Cloudflare's raw string with the exported `CF_MODEL`
- [x] 4.3 Have `generate_suggestions()` return `llmProvider` (`gemini` | `groq` | `cloudflare`) and `llmModel` alongside `suggestions` / `overallComment`, including on the salvage and retry paths, and leave the 503 error shape unchanged
- [x] 4.4 Return those fields from `POST /suggestions` and log the winning provider/model on success
- [x] 4.5 Accept `llmProvider` / `llmModel` on `POST /histories`, include them in `PUT /histories/{id}`'s allowed-field map (without clearing them when unmentioned), and return them from the history read queries in `db_helper.py`

## 5. Backend critique-quality rules

- [x] 5.1 Add to hard rules 【一】: recommended forms MUST be written in Japanese, and only 添削対象 may be corrected (the 原文 is reference material, never the object of correction)
- [x] 5.2 Extend 【三】 with the near-synonym prohibition (interchangeable alternatives are not faults; a reported wording item must name a concrete defect), the collocation-validity check on any proposed form, and the meaning-transfer framing requirement (what a Japanese reader would misunderstand, not which word maps to which)
- [x] 5.3 Rebuild `FEW_SHOT_EXAMPLE` so every recommended form is Japanese, no item rests on synonym preference, at least one item is a meaning-transfer/modality fault explained by its reader-facing consequence, while keeping ≥5 distinct items, the category spread, and one item without `sourceExcerpt`
- [x] 5.4 Add the matching clauses to the per-request reminder in `build_user_prompt` (concise, no new colon-label formats)
- [x] 5.5 Update the module docstring in `prompts.py` with a dated note for this change, following the existing changelog-style convention

## 6. Backend mechanical guard

- [x] 6.1 Add a pure predicate to `backend/app/llm/parser.py` that flags a `reason` only when a recommendation-introducing pattern is followed by a quoted span that contains no kana *and* contains at least one Simplified-only character from a curated set
- [x] 6.2 Wire it into `_content_usable()` in `suggestions.py` with a dedicated retry nudge instructing that recommended forms must be Japanese, reusing `MAX_PARSE_RETRY_ATTEMPTS` so the attempt ceiling does not change
- [x] 6.3 Verify budget-exhaustion behaviour is unchanged: the last result is still returned rather than raising

## 7. Backend tests

- [x] 7.1 New `backend/tests/test_prompt_settings.py`: default read when no row, save + read round trip, empty and oversized rejection, reset idempotence, 401 unauthenticated, 403 non-allow-listed
- [x] 7.2 Extend `test_llm_prompts.py`: `SYSTEM_PROMPT == BODY + OUTPUT_CONTRACT`; override replaces only the body; contract present with an override that never mentions JSON; exemplar ordering (rules before contract); few-shot assertions for the new rules (Japanese-only recommendations, ≥5 distinct items, one without `sourceExcerpt`)
- [x] 7.3 Extend `test_llm_suggestions.py`: override threading into provider messages; settings-read failure falls back to the default; `llmProvider`/`llmModel` reported for each winning provider, for the failover path, and for an in-provider retry model
- [x] 7.4 Extend `test_llm_parser.py`: the new predicate fires on `改为“理论上”` / `改为“对比睡眠数据”`-style reasons and does NOT fire on kanji-only Japanese citations (e.g. 「叙事詩」), Japanese-with-kana recommendations, or the existing fixture corpora
- [x] 7.5 Extend `test_pending_histories.py`: provenance persisted on create, preserved through confirm/update, and absent-safe when omitted
- [x] 7.6 Run `pytest -m "not integration"` and confirm no regressions

## 8. Frontend settings dialog

- [x] 8.1 Add `frontend/src/components/ui/dialog.tsx` (shadcn Radix Dialog wrapper — dependency already present) following the existing `sheet.tsx` conventions and MD3 tokens
- [x] 8.2 Add `settingsAPI.getPrompt()` / `updatePrompt()` / `resetPrompt()` to `frontend/src/app/api.ts` using the shared authenticated fetch helper, with types for the read shape
- [x] 8.3 Build the prompt settings dialog component: scrolling textarea pre-filled with the effective prompt, default-vs-customized indicator with editor and timestamp, character count, live validation, save/reset/cancel, inline error area, success toast, and the note that offline mode uses its own built-in prompt
- [x] 8.4 Gate save on changed-and-valid text; keep the user's text on save failure; discard edits on cancel; confirm before reset
- [x] 8.5 Enable the top-bar gear button in `frontend/src/app/page.tsx` (remove `disabled` and the "Coming Soon" title, give it an accessible name) and mount the dialog so opening/closing does not touch session state, drafts, or the job queue

## 9. Frontend provenance display

- [x] 9.1 Add `llmProvider` / `llmModel` to the suggestions response type and the history create/read types in `api.ts`
- [x] 9.2 Capture provenance in `processJobAsync`: from the API response for cloud jobs, from the WebLLM model constant for offline jobs; carry it on the queued job and pass it to `createHistory`
- [x] 9.3 Set `lastSuggestionSource` on generation completion so the existing クラウドAPI / ローカルAI badge renders, and set the model state alongside it
- [x] 9.4 Render the `{model} used` caption in the AI Suggestions panel header with metadata typography and muted colour, wrapping/truncating instead of displacing the count and selection badges, and omitted entirely when the model is unknown
- [x] 9.5 Populate the caption from the stored `llmModel` when a saved history round is restored, and show nothing for rounds saved before provenance existed

## 10. WebLLM offline parity

- [x] 10.1 Add condensed clauses to `frontend/src/lib/webllm/prompts/system.ts` covering Japanese-only recommended forms, target-only correction scope, and no synonym-preference items — kept to a few clauses for the 7B instruction budget
- [x] 10.2 Adjust the WebLLM few-shot if any of its recommended forms or items conflict with 10.1
- [x] 10.3 Update the WebLLM prompt jest tests for the new clauses

## 11. Frontend tests

- [x] 11.1 Test the settings dialog: loads the effective prompt, shows customized attribution, save calls `PUT` with the edited text, reset calls `DELETE`, save disabled while unchanged, failure keeps the text and shows the message
- [x] 11.2 Test `settingsAPI` request shapes (URL, method, auth header, body)
- [x] 11.3 Test the model caption: renders `{model} used` when provenance is known, renders nothing when unknown, and that `createHistory` receives `llmProvider`/`llmModel`
- [x] 11.4 Run `npm test` and `npm run lint` in `frontend/` with no new failures

## 12. Live validation

- [x] 12.1 Add `backend/scripts/live_critique_quality.py` (existing `live_*.py` pattern) with the reported Toronto primate-sleep passage as a fixture, reporting per-run counts of Simplified-only recommended forms, items whose excerpt is not a target-text span, synonym-preference-only items, and whether 「９点５時間」 is caught
- [ ] 12.2 Run it against the pre-change prompt and the rewritten prompt on at least two replicates per condition, and record the numbers in `design.md` — **blocked: no provider credentials in this environment; command and acceptance bar recorded in `design.md` (Validation Results)**
- [ ] 12.3 Confirm latency and suggestion counts stay within the existing budget (no Gemini timeouts introduced by the longer rules) and record them — **blocked on 12.2 (same credentials); the probe already reports `elapsed_s` / `finishReason` / token counts per row**
- [ ] 12.4 Probe once with a saved custom prompt to confirm the override reaches the provider and the output contract still holds — **blocked on credentials; `CRITIQUE_PROBE_PROMPT_FILE` condition implemented and exercises the same `system_prompt_override` path**

## 13. Documentation

- [x] 13.1 Update `AGENTS.md`: editable prompt behavior and its code-owned contract, `app_settings` table, `llm_provider`/`llm_model` columns, new `/settings/prompt` endpoints, response fields, and the new critique rules in the prompt-maintenance section
- [x] 13.2 Update `docs/SYSTEM-DESIGN.md`: data model, API list, prompt resolution flow, provenance flow
- [x] 13.3 Update `docs/UI-DESIGN.md`: settings dialog pattern (new `Dialog` primitive) and the metadata caption token usage
- [x] 13.4 Run `openspec validate editable-prompt-model-log-and-critique-fix --strict`

## 14. Manual verification

- [x] 14.1 Generate once: caption shows the model, history row stores provider and model, badge shows クラウドAPI — verified in two halves: the history round trip against a real Postgres, and the caption plus クラウドAPI badge in `modelProvenance.test.tsx` driving the real generation path with a mocked API
- [x] 14.2 Save a prompt edit, generate again, confirm it took effect without redeploy; reset and confirm the default returns — verified against a real Postgres: the stored body is what `build_messages()` composes (contract still appended), and reset deletes the row and restores the default
- [x] 14.3 Confirm a second browser session sees the saved prompt without re-entry — the prompt is one global row keyed only by `correction_system_prompt`, and an independent request after the save read the stored text back with its attribution
- [ ] 14.4 Re-run the reported passage and confirm no critique hands back a Chinese form as the correction, none critiques the source text, and synonym-only items are gone — **blocked on provider credentials; this is what `backend/scripts/live_critique_quality.py` scores (see `design.md` Validation Results for the command)**
