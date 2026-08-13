## Why

A production run on 2026-08-13 23:07 returned only **3 suggestions** for a 3-paragraph, 704-character TARGET — one per paragraph — despite prompts targeting at least five. Live `generateContent` probes against the 5-paragraph epic fixture show the cause is *not* the output-token budget: `generationConfig.maxOutputTokens` is correctly delivered as 8192, `finishReason` is `STOP` (never `MAX_TOKENS`), and only 952–1067 completion tokens are actually consumed (~13% of the budget, against a 65536 model output cap).

The binding constraint is Gemini 3.x Flash's **default thinking mode**. Each call burns 2920–3798 `thoughtsTokenCount`, which has two harmful effects: latency reaches 20.7–21.0 s against the 22 s HTTP timeout (2 of 4 default-mode probes timed out outright and fell over to Groq), and the model spends its budget on internal deliberation then emits a *shorter, more selective* critique — 7 suggestions on a 5-paragraph fixture, consistent with 3 on a 3-paragraph one. Setting `thinkingConfig.thinkingLevel = "low"` eliminates thought tokens, drops latency to 6.7–15.6 s with no timeouts, and raises coverage to 8–19 suggestions on the same fixture and prompt.

## What Changes

- Set `generationConfig.thinkingConfig.thinkingLevel` to `"low"` on Gemini `generateContent` requests, overridable via a new optional `GEMINI_THINKING_LEVEL` environment variable (values `low` / `high` / `none`, where `none` omits the field and restores provider-default thinking).
- Raise `generationConfig.maxOutputTokens` from 8192 to 16384 as headroom insurance. Low-thinking responses consume 1252–2090 completion tokens today, but coverage rises with thinking disabled and long homework could grow further; the model's advertised `outputTokenLimit` is 65536, so 16384 stays well inside the cap and cannot cause a 400.
- Log Gemini `usageMetadata` (`promptTokenCount`, `candidatesTokenCount`, `thoughtsTokenCount`, `totalTokenCount`) alongside the existing `finishReason` line, so token headroom and thinking cost are diagnosable in production without a probe script.
- Add `backend/scripts/live_gemini_coverage.py`, a live probe that reports suggestion count, `finishReason`, usage metadata, latency, and the model's advertised token limits, and can sweep `maxOutputTokens` / `thinkingConfig` settings.
- Add deterministic unit tests for the payload shape (thinking level, env override, token budget), the usage-metadata logging, and a parser regression asserting truncated multi-item JSON retains every complete item rather than only the leading few.

Deliberately unchanged: failover order (Gemini → Groq → Cloudflare), `GEMINI_TIMEOUT` (22 s), `SUGGESTIONS_WALL_CLOCK_S` (55 s), Vercel `maxDuration` (60 s), WebLLM's オフラインモード-only gating, and the JSON response schema. The prompt-side cardinality anchoring (3-item few-shot) is out of scope here — it is addressed by the concurrent `refine-prompt-instruction-coherence` change.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `ai-suggestions`: Gemini requests MUST constrain internal thinking so a homework-length critique completes well inside the provider timeout and covers multi-paragraph TARGET text densely; the output-token budget MUST stay within the model's advertised cap; token usage MUST be observable in logs; and truncation salvage MUST preserve every complete suggestion.

## Impact

- `backend/app/llm/gemini_provider.py` (payload `generationConfig`, usage logging)
- `backend/scripts/live_gemini_coverage.py` (new live probe)
- `backend/tests/test_gemini_provider.py`, `backend/tests/test_llm_parser.py`
- `AGENTS.md`, `docs/SYSTEM-DESIGN.md` (documented token/thinking/latency numbers)
- No API, DB, schema, failover, secret, or frontend changes
