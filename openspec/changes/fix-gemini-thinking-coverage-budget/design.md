## Context

`POST /suggestions` runs Gemini → Groq → Cloudflare. Users reported thin critiques (3 suggestions on a multi-paragraph TARGET) and asked whether the output-token budget was the cause. Two prior changes had already moved in that direction: `fix-critique-format-and-gemini-coverage` raised `maxOutputTokens` 4096 → 8192 and added `finishReason` logging, and `fix-vercel-gemini-timeout` cut `GEMINI_TIMEOUT` 45 → 22 s to fit Vercel's 60 s `maxDuration`. Neither fixed the symptom, so this change starts from measurement rather than inference.

### Evidence gathered

Direct DB evidence for the reported symptom (`correction_histories` / `ai_proposals` on the shared Supabase project):

| Field | Value |
|---|---|
| timestamp | 2026-08-13 23:07:01 |
| `provider` | `api` (cloud path, not WebLLM) |
| TARGET length / paragraphs | 704 chars / 3 |
| proposals persisted | **3** (one per paragraph) |
| mean `original_reason` length | 113 chars (long, Gemini-style pedagogical Chinese) |

Live `generateContent` probes via `backend/scripts/live_gemini_coverage.py` on `backend/tests/fixtures/epic_shi_source_target.py` (5-paragraph TARGET, identical prompt), 2 calls per model per setting:

| Setting | Model | Elapsed | `finishReason` | `candidatesTokenCount` | `thoughtsTokenCount` | Suggestions |
|---|---|---|---|---|---|---|
| default thinking | 3.7-flash | **TIMEOUT** @22.0 s | — | — | — | — |
| default thinking | 3.7-flash | 20.69 s | STOP | 1067 | 3798 | 7 |
| default thinking | 3.6-flash | 20.98 s | STOP | 952 | 2920 | 7 |
| default thinking | 3.6-flash | **TIMEOUT** @22.1 s | — | — | — | — |
| `thinkingLevel: low` | 3.7-flash | 7.40 s | STOP | 1369 | none | 10 |
| `thinkingLevel: low` | 3.7-flash | 12.64 s | STOP | 1252 | none | 9 |
| `thinkingLevel: low` | 3.6-flash | 15.62 s | STOP | 2090 | none | 19 |
| `thinkingLevel: low` | 3.6-flash | 11.46 s | STOP | 1596 | none | 17 |
| `thinkingBudget: 0` | 3.7-flash | 6.71 s | STOP | 1472 | none | 10 |
| `thinkingBudget: 0` | 3.6-flash | **HTTP 400** INVALID_ARGUMENT | — | — | — | — |

Advertised model limits (both pooled models): `inputTokenLimit` 1048576, `outputTokenLimit` **65536**.

### Conclusions the evidence forces

1. **The token budget was never the constraint.** `maxOutputTokens: 8192` was correctly placed in `generationConfig` and delivered; `finishReason` was `STOP` on every successful call, never `MAX_TOKENS`; and peak observed completion usage was 2090 tokens — 26% of the 8192 budget. The user's "出力トークン足りてますか" question resolves to *yes, with 4× headroom*.
2. **Default thinking mode is the constraint, in two ways.** It costs 2920–3798 thought tokens, pushing latency to 20.7–21.0 s against a 22 s timeout — 2 of 4 default-mode calls timed out and fell over to Groq. And it makes the model *more selective*: 7 suggestions on 5 paragraphs (~1.4/paragraph), which extrapolates cleanly to the 3-on-3-paragraphs production record.
3. **`thinkingLevel: "low"` fixes both.** Latency 6.7–15.6 s (no timeouts in 5 calls), coverage 8–19 suggestions (~2–4/paragraph), `finishReason` still `STOP`.
4. **`thinkingBudget` is not portable.** It works on `gemini-3.7-flash` but returns HTTP 400 INVALID_ARGUMENT on `gemini-3.6-flash`, so the pool must use `thinkingLevel`.
5. **The parser is not dropping items.** One low-thinking `gemini-3.6-flash` response arrived without a closing brace, and the parser still recovered 17 complete suggestions — `extract_json`'s depth-tracking scan plus LIFO `repair_truncated_json` already do the right thing. A regression test locks this in rather than a behavior change.

### Constraints

- Failover order and WebLLM gating are fixed by the task brief.
- `GEMINI_TIMEOUT` (22 s) + `GROQ_TIMEOUT` (25 s) + `CF_TIMEOUT` (20 s) already sum past `SUGGESTIONS_WALL_CLOCK_S` (55 s), so the Gemini timeout has no room to grow without eating failover budget.

## Goals / Non-Goals

**Goals**
- Restore dense multi-paragraph coverage from the primary provider.
- Remove the near-timeout latency cliff that silently demotes Gemini to Groq.
- Make token headroom and thinking cost visible in production logs.
- Prove the parser preserves complete items on truncation.

**Non-Goals**
- Changing failover order, provider timeouts, the wall-clock budget, or `maxDuration`.
- Prompt-text changes: the 3-item few-shot's cardinality anchoring is the concurrent `refine-prompt-instruction-coherence` change's scope, and editing `prompts.py` here would conflict with it.
- Reviving WebLLM auto-fallback.
- Any frontend change.

## Decisions

### Constrain thinking with `thinkingLevel`, defaulting to `low`

`generationConfig.thinkingConfig.thinkingLevel = "low"`, read from `GEMINI_THINKING_LEVEL` when set.

- **Why `thinkingLevel` over `thinkingBudget`**: `thinkingBudget: 0` is rejected with HTTP 400 by `gemini-3.6-flash`. Since the provider rotates randomly across `ALLOWED_GEMINI_MODELS`, a per-model-invalid field would make ~50% of requests fail hard. `thinkingLevel: "low"` was accepted by both.
- **Why `low` and not the provider default**: default thinking is what produced the thin, near-timeout responses. Low thinking measured strictly better on all three axes that matter here (latency, coverage, no truncation) with no observed quality loss — `gemini-3.7-flash` reasons stayed 92–240 chars, comparable to or longer than the 113–172 chars of default-thinking runs.
- **Why an env override with a `none` opt-out**: if a future model's low-thinking quality regresses, ops can set `GEMINI_THINKING_LEVEL=high` or `=none` and redeploy, without a code change. `none` omits `thinkingConfig` entirely rather than sending a literal `"none"`, so the escape hatch cannot itself become a 400.

### Raise `maxOutputTokens` 8192 → 16384

Not because 8192 was being hit — it was not — but because disabling thinking *increases* emitted suggestions, and the highest observed usage already rose from 1067 to 2090 tokens. A longer real assignment with more paragraphs could plausibly multiply that. 16384 is 8× the observed peak and 25% of the 65536 model cap, so it cannot trigger the "value above model limit ⇒ 400" failure mode the task brief warned about. Since Gemini bills emitted tokens rather than the requested ceiling, an unused ceiling costs nothing.

### Timeout trade-off: keep 22 s

Considered raising `GEMINI_TIMEOUT` so default-thinking calls would stop timing out, and rejected it. The chain already over-commits: 22 + 25 + 20 = 67 s of provider timeouts against a 55 s wall clock. Raising Gemini's share would make a slow-Gemini request more likely to consume the whole budget and return 503 without Groq or Cloudflare ever being tried. Attacking latency at its source is strictly better: with low thinking the observed maximum is 15.6 s, so 22 s now carries ~40% headroom instead of the ~5% it had before. `SUGGESTIONS_WALL_CLOCK_S` (55 s) and Vercel `maxDuration` (60 s) therefore stay as-is.

### Log `usageMetadata` next to `finishReason`

One INFO line per response with prompt / candidate / thoughts / total counts. This is what turned an unfalsifiable "maybe tokens are short" hypothesis into a measurement, and it is cheap to keep. Extraction must tolerate a missing `usageMetadata` so a shape change upstream cannot break generation.

## Risks / Trade-offs

- **Low thinking could reduce per-reason depth on inputs unlike the fixture.** Mitigated by the `GEMINI_THINKING_LEVEL` override and by the measured reason lengths, which did not shrink. Existing Chinese/JSON content checks and the `MAX_PARSE_RETRY_ATTEMPTS` loop still guard quality.
- **More suggestions means more output tokens and slightly more latency per call.** Absorbed by the raised ceiling and the large new timeout headroom.
- **`thinkingLevel` is a newer API field.** If a future pooled model rejects it, the failure is a hard 400 on that model; the in-provider rotation retries the second model, and `GEMINI_THINKING_LEVEL=none` disables the field fleet-wide. A unit test pins the field name, and the live probe re-verifies acceptance per model.
- **Probe results are small-n (2 calls per cell) and rate-limit sensitive.** Groq keys were already 429-throttled during probing, so cross-provider comparison is indicative only. The Gemini default-vs-low contrast is large enough (2 timeouts vs 0; 7 vs 8–19 suggestions) that small-n does not threaten the conclusion.

## Migration Plan

Code-only, no schema or API change. Deploy applies on the next Vercel Production build. `GEMINI_THINKING_LEVEL` is optional — absent means `low`. Rollback is setting `GEMINI_THINKING_LEVEL=none` (no redeploy of code needed, just an env change plus redeploy) or reverting the commit.

Operational note surfaced while probing: the local docker backend's `env_file` snapshot predates the Gemini keys in `conf/.env`, so `mjai-backend-1` has no `GEMINI_*` in its environment and silently serves local suggestions from Groq/Cloudflare. `docker compose up -d --force-recreate backend` fixes it. This is a local-only env staleness issue, not a code defect, and is documented rather than coded around.

## Open Questions

- None blocking. Whether `high` thinking with a much larger timeout would beat `low` on critique depth is worth revisiting only if users report shallow reasons, and would require the wall-clock budget to be re-derived first.
