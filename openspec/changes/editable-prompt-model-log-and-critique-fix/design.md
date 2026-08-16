## Context

See `proposal.md` for motivation. Constraints that shape the approach:

- The correction prompt is assembled in `backend/app/llm/prompts.py` as three code constants: `SYSTEM_PROMPT` (≈2,250 chars of Simplified-Chinese rules in sections 【一】–【五】, ending with a `格式：` line that states the JSON response schema), `FEW_SHOT_EXAMPLE`, and a per-request reminder inside `build_user_prompt`. `EXEMPLAR_REFERENCE_RULES` is appended to the system prompt only when an exemplar translation is supplied. `build_messages()` emits `[system, few-shot user, request user]`.
- Generation runs on Vercel with `maxDuration` 60s. `suggestions.py` enforces a 55s soft wall clock and shares one `MAX_PARSE_RETRY_ATTEMPTS = 4` budget across JSON-parse failures and the Chinese-language checks in `parser.py`.
- Gemini and Groq each pick a model per request from an allow-list and may retry once on a second model; Cloudflare has a fixed model. All three `call_*` entry points return a bare `str`, so the winning model exists only in log lines.
- `correction_histories.provider` already exists but means *transport* (`api` | `webllm`). Rows are created by the frontend (`historyAPI.createHistory`) at generation time with `status=pending`, keyed by `clientJobId`.
- Postgres access is per-operation `asyncpg.connect(..., statement_cache_size=0)` through the Supabase pooler — there is no connection pool, so every DB touch costs a connection.
- The top-bar gear button already exists but is `disabled` with `title="Settings (Coming Soon)"`. `frontend/src/components/ui/` has `sheet.tsx` (Radix Dialog) but no `dialog.tsx`; `@radix-ui/react-dialog` is already a dependency. There is no SWR/React Query — data is `useState` + `useCallback` loaders in `page.tsx`.
- The reported bad critiques were produced by an unknown member of the rotation pools, which is precisely the gap the provenance work closes.

## Goals / Non-Goals

**Goals:**

- One shared prompt record that a non-deploying user can edit, with a recovery path that cannot be locked out by a bad edit.
- Provenance (provider + exact model) available in the response, in the database, and glanceable in the UI.
- Default critique rules and few-shot exemplar that make the reported failure modes non-compliant, with one mechanical check for the failure mode that is detectable from output text alone.
- No increase in worst-case request latency ceiling: no new retry attempts, no new provider timeouts.

**Non-Goals:**

- Prompt version history, diffing, or per-history prompt snapshots (only reset-to-default).
- Per-user or per-session prompt variants; the record is global by design.
- Making the offline WebLLM path consume the stored custom prompt.
- Editing the few-shot exemplar, reminder text, or retry nudges from the UI.
- Tightening RLS to per-user scope (unchanged permissive policies, as elsewhere in this app).
- Changing the failover order, provider timeouts, or the wall-clock budget.

## Decisions

### 1. Storage: generic `app_settings` key/value table, one row for the prompt

**Choice**: new table `app_settings(setting_key TEXT PRIMARY KEY, setting_value TEXT NOT NULL, updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_by TEXT)`, with the prompt stored under key `correction_system_prompt`. Absence of the row means "default in effect"; reset deletes the row rather than writing the default text into it.

**Rationale**: a primary-key lookup is the cheapest possible read on the one hot path (generation). Storing *absence* rather than a copy of the default means a future default improvement automatically reaches anyone who has not customized the prompt — writing the default text into the row at first read would silently freeze today's wording forever. Key/value also lets the next tunable (few-shot exemplar, thinking level) land without a migration.

**Alternatives considered**:
- Dedicated `prompt_settings` table with named columns — needs a migration per new tunable, no benefit at this scale.
- Row-per-version with an `is_active` flag — buys version history we explicitly deferred; adds selection logic to the hot path.
- Env var / file on the server — not editable from the UI, not shared, lost on redeploy.

### 2. Prompt decomposition: editable rules body + code-owned output contract

**Choice**: split `SYSTEM_PROMPT` into `SYSTEM_PROMPT_BODY` (the rules, editable) and `OUTPUT_CONTRACT` (the JSON-only instruction plus the `格式：` schema line). `SYSTEM_PROMPT` stays exported as `BODY + OUTPUT_CONTRACT` so existing references and tests keep a single name for the composed default. `build_system_prompt(exemplar, override=None)` composes `(override or BODY) [+ EXEMPLAR_REFERENCE_RULES] + OUTPUT_CONTRACT`.

**Rationale**: the response contract is the one part of the prompt whose loss breaks the machine interface rather than merely lowering quality. Keeping it code-owned and last makes an arbitrary user edit a quality risk, never a protocol risk, and last position also gives it recency emphasis.

**Consequence to accept**: for the exemplar case the exemplar rules now precede the contract instead of following it, so that assembled string differs byte-wise from today; the existing byte-identity assertion for that case must be updated. The no-exemplar, no-override composition stays byte-identical to today's `SYSTEM_PROMPT`.

**Alternatives considered**:
- Fully editable single blob including the schema — one careless save yields unparseable output for everyone until someone resets.
- Editable "extra instructions" appended to an immutable default — cannot fix the rules the user objects to, so it fails the actual request.
- Validating that user text mentions JSON — fragile string sniffing, and unnecessary once the contract is appended by code.

### 3. Editable scope is the rules body only in v1

**Choice**: the settings surface edits `SYSTEM_PROMPT_BODY`. The few-shot exemplar stays in code.

**Rationale**: `AGENTS.md` records the hard-won rule that rules and exemplar must move together — the exemplar's item count and issue categories anchor behaviour more strongly than the rule text does. Exposing only the rules keeps the density/category anchor intact under arbitrary edits; exposing only the exemplar would be worse. The key/value schema (Decision 1) makes adding a second editable key later a code-only change.

### 4. Override plumbing: read per request, no cache, short timeout, default on failure

**Choice**: the `/suggestions` handler reads the stored prompt (bounded by a ~3s timeout) and passes it as an explicit `system_prompt_override` argument down to `build_messages()`. No process-local cache. On timeout or error: log and use the default. The wall-clock deadline is established at request entry, so the lookup consumes the same 55s budget rather than extending it.

**Rationale**: "save then generate" must reflect the save immediately, and a TTL cache on Vercel would behave differently per warm isolate — the confusing kind of staleness. The read is one PK lookup; the request it rides on already takes seconds.

**Alternatives considered**:
- 30–60s TTL cache — saves ~100ms on a multi-second request in exchange for unpredictable "why didn't my edit apply" reports.
- Client sends the prompt with each generation — lets any client inject an arbitrary system prompt and makes the DB no longer authoritative.
- Read the prompt outside the wall-clock budget — could push total duration past `maxDuration` and turn an app-level 503 into an opaque platform 504.

### 5. Provenance capture: rotation entry points return `(text, model)`

**Choice**: introduce a small `ProviderOutput` value type (`text`, `model`) returned by `call_gemini_with_rotation()` and `call_groq_with_rotation()`; the inner `call_gemini` / `call_groq` keep returning `str`. Cloudflare, having no rotation, is paired in `suggestions.py` with its exported `CF_MODEL` constant. `generate_suggestions()` returns the parsed body plus `llmProvider` / `llmModel`, and the route passes them through.

**Rationale**: the winning model is only knowable where rotation and in-provider retry happen, so that is where it should be reported; changing only the rotation wrappers keeps the blast radius (and existing provider tests) small.

**Alternatives considered**:
- Module-level "last used model" global — wrong under concurrent invocations.
- Mutable out-parameter dict threaded through calls — obscure, easy to forget on a new provider.
- Changing every `call_*` signature — more churn across tests for no extra information.

### 6. Wire and column naming: `llmProvider` / `llmModel`, separate from `provider`

**Choice**: response fields `llmProvider` / `llmModel`; history columns `llm_provider` / `llm_model`; provider values `gemini` | `groq` | `cloudflare` | `webllm`. The existing `provider` (`api` | `webllm`) column and its UI badge are untouched.

**Rationale**: `provider` already means transport, and the UI reads it that way. Overloading it would break the cloud/local badge and lose the distinction between "which path" and "which model". Additive columns keep old rows and old clients valid.

### 7. Who writes provenance: the frontend, on the existing pending-history create

**Choice**: the frontend takes `llmProvider` / `llmModel` from the suggestions response (or the WebLLM constants offline) and includes them in the `createHistory` call it already makes when a job completes. `PUT /histories/{id}` leaves them alone unless explicitly sent.

**Rationale**: the history row is a client-driven artifact today — the backend has no history id at generation time, and inventing one would mean a second write path plus reconciliation with `clientJobId` dedupe.

**Alternative considered**: a backend-written generation audit table (would also allow recording which prompt text was used) — real value, but it is a separate capability; noted as a follow-up.

### 8. UI: metadata caption in the suggestions panel header, plus fixing the dead source badge

**Choice**: render `{model} used` as `text-metadata text-on-surface-variant` in the AI Suggestions panel header row, right-aligned, wrapping/truncating rather than displacing the count and selection badges. `title` carries the provider name. Restoring a history round sets the same state from its stored `llmModel`. Also set `lastSuggestionSource` on generation completion so the existing クラウドAPI / ローカルAI badge stops being permanently invisible.

**Rationale**: the header is the one place already reserved for metadata about the whole set, so it satisfies "邪魔じゃないところ" without touching the cards. The raw model id (`gemini-3.7-flash`, `openai/gpt-oss-120b`) is shown rather than a prettified name: it matches the provider dashboards and log lines an operator would compare against, and needs no display-name mapping to maintain as models rotate.

**Alternatives considered**:
- Per-suggestion-card badge — repeats identical information N times inside the content the user is reading.
- Toast only — ephemeral, gone by review time, and unavailable for a restored round.
- Job Queue card only — invisible while reviewing suggestions, which is when the question arises.

### 9. Settings surface: add a `dialog` primitive rather than reuse `Sheet`

**Choice**: add `frontend/src/components/ui/dialog.tsx` (shadcn Radix Dialog wrapper, no new dependency) and build the settings dialog on it. `Sheet` stays the session-navigation pattern.

**Rationale**: a multi-thousand-character prompt needs a wide centered modal with an internally scrolling textarea; the left sheet is navigation and a right sheet is too narrow for rule text. Radix gives the focus trap and Escape handling that the hand-rolled bell dropdown lacks.

### 10. Validation: non-empty, 20,000-character cap, advisory length hint

**Choice**: the server rejects empty/whitespace-only text and text over 20,000 characters with a 400 that states the limit; the dialog shows a live character count and an advisory (non-blocking) note when the text greatly exceeds the default length.

**Rationale**: the default body is ≈2,250 characters, so the cap is ~8x headroom — enough for substantial rule expansion while bounding worst-case prompt tokens, since CJK text is roughly one token per character and a runaway prompt would eat into the Gemini 22s timeout.

### 11. Mechanical guard for Chinese recommended forms: narrow triple condition, existing retry budget

**Choice**: add a pure predicate in `parser.py` that flags a `reason` when all three hold: (a) it contains a recommendation-introducing pattern (改为 / 改成 / 宜改为 / 应改为 / 换成 / 建议改为 …) followed by a quoted span, (b) that span contains no kana, and (c) that span contains at least one Simplified-only character from a curated set (对, 论, 实, 现, 语, 时, 说, 标, 脑, 据 …). Wire it into `_content_usable()` with its own retry nudge instructing that recommended forms must be written in Japanese. It reuses `MAX_PARSE_RETRY_ATTEMPTS`, so the worst-case attempt count and latency ceiling are unchanged.

**Rationale**: the reported `改为“理论上”` / `改为“对比睡眠数据”` outputs are not "lower quality", they are unusable — a learner cannot write 「理论上」 into a Japanese sentence. Condition (b) alone would false-positive on legitimate kanji-only Japanese citations such as 「叙事詩」; requiring a Simplified-only character makes the check specific. Because this is script-level detection it is deliberately conservative: it will not catch a recommendation that is *script-legal* Japanese but semantically wrong (the reported 必要 → 需要 case — 需要 is a real Japanese word), which is why the rule and exemplar work in Decision 12 carries the primary load and this guard is only a floor.

**Alternatives considered**:
- CI-only heuristic like `has_weak_critique_reason` (not wired into retry) — leaves known-unusable output reaching the user.
- Per-character Simplified/Traditional conversion library — a new dependency and a heavier check for a narrow gain.
- Rejecting the whole response with an error — worse than returning the last result after the budget, which is the established behaviour.

### 12. Default prompt rewrite: extend the hard-rule and priority sections, then rebuild the exemplar

**Choice**: add to the hard rules (【一】) that recommended forms must be Japanese and that only 添削対象 may be corrected; extend the teaching-priority section (【三】) with the near-synonym prohibition, the collocation-validity check on any proposed form, and the meaning-transfer framing requirement; then rebuild `FEW_SHOT_EXAMPLE` so every recommended form is Japanese, no item is a bare synonym preference, and at least one item is a meaning-transfer/modality fault explained by its reader-facing consequence — while keeping ≥5 distinct items, the category spread, and the one item without `sourceExcerpt`.

**Rationale**: this is the `AGENTS.md` prompt-maintenance rule applied literally — rule text alone has repeatedly failed to move behaviour when the exemplar demonstrated something else. The reported session is evidence: 【三】 already forbade non-teaching source-token matching, yet three of the five reported items were exactly that.

**Also**: mirror a condensed form of the three new rules into the WebLLM system prompt so the offline path is not left with the failure modes we just declared non-compliant. That prompt is deliberately terse for a 7B model, so the mirror is two or three clauses, not a port.

### 13. Live validation before claiming the fix works

**Choice**: add `backend/scripts/live_critique_quality.py` following the existing `live_*.py` probe pattern, using the reported passage (Toronto primate-sleep text) as a fixture, and report per-run counts of: recommended forms containing Simplified-only characters, items whose flagged excerpt is not a span of the target text, items whose justification is synonym preference only, and whether the Chinese-numeral carryover 「９点５時間」 is caught as a substantive fault. Run it against the current prompt and the rewritten prompt.

**Rationale**: every previous prompt change in this repo that stuck was backed by a live probe; a rules diff alone cannot show whether the model's behaviour moved. The 「９点５時間」 check is the positive control — the class of fault the current prompt spends its items *not* reporting.

## Validation Results

**Automated (run in this environment):**

- Backend `pytest -m "not integration"`: green, including the new `test_prompt_settings.py` and the extended prompt/suggestions/parser/history suites.
- Frontend `npm test`: 266 tests across 21 suites green, including the settings-dialog, `settingsAPI` request-shape, WebLLM-clause, and model-caption/provenance-persistence tests. `npm run lint` reports only the pre-existing `no-page-custom-font` warning; `tsc --noEmit` is clean.
- Scorer of `backend/scripts/live_critique_quality.py` checked offline against two synthetic critiques: the reported failing output scores `chinese_forms=3` (对比睡眠数据 / 理论上 / 实现), `source_items=1` (完成了逐渐独特的进化 — an excerpt from the Chinese source, not the Japanese target), `synonym_only=3`, `numeral_caught=false`; a compliant critique scores zero on all three and `numeral_caught=true`. So the metrics do discriminate the reported failure mode before any live call is made.

**End-to-end against a real Postgres (run in this environment):** a local Postgres 16 was created, all seven migrations applied in order (006 and 007 re-applied to confirm idempotence), and the FastAPI app run against it with a self-minted HS256 JWT:

| Check | Result |
|---|---|
| `GET /settings/prompt` with no row | `isCustomized: false`, `systemPrompt == defaultSystemPrompt`, attribution `null`, and the `格式：` contract line absent from the editable body (2,694 chars) |
| `PUT /settings/prompt` | Trims, stores, returns `isCustomized: true` with `updatedBy` from the JWT email and `updatedAt` set; a subsequent independent request reads the stored text back, which is what makes another browser session see it without re-entry |
| Validation / auth | Whitespace-only → 400 `systemPrompt must not be empty`; 20,001 chars → 400 stating the limit; no token → 401; non-allow-listed email → 403 |
| Override reaches the prompt | `resolve_system_prompt_override()` returned the stored body, `build_messages()` composed it as the body with `OUTPUT_CONTRACT` still appended and the default body gone, and the no-override composition stayed byte-identical to `SYSTEM_PROMPT` |
| `DELETE /settings/prompt` | Default restored, attribution back to `null`, row count 0, second delete also 200 (idempotent) |
| Provenance round trip | `POST /histories` with `llmProvider: gemini` / `llmModel: gemini-3.7-flash` reads back on the session's history list; `PUT /histories/{id}` promoting `pending` → `confirmed` without mentioning provenance preserved both values |
| No-keys behaviour | `POST /suggestions` still returns the unchanged 503 shape (`error` / `fallback_available` / `message`) |

**Supabase CLI migration path (rehearsed in this environment):** the same local Postgres was rebuilt with only 001-005 applied, then driven with Supabase CLI 2.114.0 to establish what the operator step actually requires:

| Step | Result |
|---|---|
| `supabase migration list --workdir backend --db-url …` | Accepts the `001_`-style versions and reports all seven as local-only, i.e. an empty remote history |
| `supabase db push` with that empty history | Fails on `001_initial_schema.sql` with `relation "sessions" already exists` — 001 and 002 are not idempotent, so the naive command cannot be the instruction we hand over |
| `supabase migration repair --status applied 001 … 005` | Records the five versions without re-running their SQL; `migration list` then shows 006/007 as the only pending ones |
| `supabase db push` after repair | Applies exactly 006 and 007; `app_settings` exists, `correction_histories` gains `llm_provider`/`llm_model`, and the history table holds 001-007 |
| Re-running `db push` | `Remote database is up to date.` — safe to press twice |

`.github/workflows/apply-migrations.yml` encodes this as a manual workflow so the shared project can be migrated from the existing `DATABASE_URL` secret rather than by pasting DDL. It also rewrites a pooler URL's port 6543 (transaction mode, no DDL) to 5432 (session mode) and masks the value in the log.

**Live LLM probe (blocked in this environment — no provider credentials):**

`GEMINI_API_KEY(S)` / `GROQ_API_KEY(S)` are not present and there is no `conf/.env`, so the probe exits 2 (`GEMINI_API_KEY(S) not configured; skipping probe`) rather than producing numbers. Tasks 12.2–12.4 (baseline-vs-current replicates, latency/count budget check, and the custom-prompt override probe) therefore stay open and must be run by an operator who has keys:

```bash
set -a && . conf/.env && set +a
git show <pre-change-sha>:backend/app/llm/prompts.py > /tmp/old_prompts.py
cd backend && PYTHONPATH=. \
  CRITIQUE_PROBE_BASELINE_PROMPTS_FILE=/tmp/old_prompts.py \
  CRITIQUE_PROBE_ITERS=2 python scripts/live_critique_quality.py
# then, for 12.4, save an edited prompt body and re-run with:
#   CRITIQUE_PROBE_PROMPT_FILE=/tmp/custom_body.txt
```

The probe reports `elapsed_s` against `GEMINI_TIMEOUT` and `finishReason` / token counts on every row, which is what 12.3 needs: the acceptance bar is no `TIMEOUT` rows and `n_suggestions` no lower than baseline. No numbers are recorded here because none were measured — inventing them is exactly what the probe exists to prevent.

## Risks / Trade-offs

- **[Risk] A bad prompt edit degrades critique quality for everyone, silently** → the output contract is code-owned so responses stay parseable; reset-to-default is one click and does not depend on the stored text being valid; attribution shows who last saved it.
- **[Risk] Prompt edits are unversioned, so a past critique cannot be tied to the text that produced it** → accepted for this change; provenance covers the model half of that question. Follow-up: store a prompt hash or `updated_at` on the history row.
- **[Risk] Extra DB read per generation (one more pooler connection, ~50–200ms)** → 3s timeout, inside the existing 55s budget, default-on-failure; negligible against multi-second inference.
- **[Risk] Long custom prompts raise prompt tokens and latency against the Gemini 22s timeout** → 20,000-char cap plus an advisory hint in the dialog; failover to Groq/Cloudflare still applies if the primary times out.
- **[Risk] The Chinese-recommendation guard false-positives and burns an attempt** → triple condition, unit-tested against legitimate kanji-only citations and the existing fixtures; worst case is one extra attempt inside a budget that already exists.
- **[Risk] The guard cannot catch script-legal but wrong recommendations (需要 for 必要)** → explicitly out of the guard's reach; addressed by rules + exemplar and measured by the live probe rather than pretended away.
- **[Risk] Shared last-write-wins prompt lets one edit overwrite another** → visible attribution and timestamp; acceptable for an allow-listed, effectively single-operator app, and cheaper than optimistic-concurrency plumbing.
- **[Risk] New columns/table deployed before the shared Supabase project is migrated would break history writes** → the migrations are hand-applied, so this order is realistic rather than hypothetical: history reads/writes probe `information_schema` once per process and drop the two columns when absent, a missing `app_settings` table serves the built-in prompt on read and a 503 naming the migration on save, and the generation path defaults the prompt. Both migrations are still required for the features to do anything (see Migration Plan).
- **[Trade-off] Raw model ids in the UI** → slightly technical for an end user, but exactly matchable against provider dashboards and logs, and no display-name table to maintain as pools rotate.
- **[Trade-off] Offline WebLLM keeps its own prompt** → the settings surface states this, so the divergence is disclosed rather than surprising.

## Migration Plan

1. Apply `006_app_settings.sql` and `007_history_llm_provenance.sql` to the shared Supabase project. Both are additive and idempotent (`CREATE TABLE IF NOT EXISTS`, `ADD COLUMN IF NOT EXISTS`), so the currently deployed code keeps working against the migrated schema, and the new code tolerates the un-migrated one (see the schema probe below), so deploy order is not load-bearing. Either run `.github/workflows/apply-migrations.yml` (`mode=list` first, then `mode=push`) or the same Supabase CLI commands locally. **`supabase db push` alone fails**: 001-005 were applied through the SQL Editor, so the remote migration history can be empty, and `001_initial_schema.sql` is not idempotent (`relation "sessions" already exists`). Pass `repair_versions="001 002 003 004 005"` when the history is empty — repair records versions without re-running their SQL.
2. Deploy backend and frontend together (one Vercel monorepo deploy). No feature flag: with no `app_settings` row the effective prompt is the new default, which is the intended behaviour.
3. Verify after deploy: generate once and confirm the response carries `llmProvider` / `llmModel`, the caption renders, and the history row stores both; open the settings dialog, save a trivial edit, generate again to confirm it took effect, then reset.
4. Rollback: revert the deploy. The table and columns can stay — old code ignores both. A prompt edit that turns out to be harmful does not require a rollback at all: reset-to-default is the faster remedy.

## Open Questions

- Whether to promote the few-shot exemplar to a second editable key later, once there is evidence that rule-only editing is too blunt. Deferrable: the storage shape already allows it and no spec here forbids it.
- Whether history rows should also record the prompt text (or a hash) in force at generation time. Deferrable: it needs its own retention and display decisions, and does not change any requirement in this change.
