## Why

The critique prompts have accumulated eight changes' worth of rules (Chinese-only fields, why-in-every-reason, accessibility, quote policy, anti-fabrication, teaching bar, anti-label formatting, coverage density). An audit of the resulting text shows the *content* requirements are all present, but the *exemplars and hedges* now work against them: both few-shots demonstrate only 3 suggestions and only lexical/register issue types, one WebLLM few-shot item repeats an earlier item's point (padding-by-repetition, which the rules forbid), a backend few-shot `reason` contains meta-instruction text aimed at the model, and the coverage MUST sits in the same sentence as `质量优先于条数` plus a global `宜简明` cue. Models imitate demonstrated cardinality and issue categories far more strongly than they obey a numeric target, so these are the most likely remaining drivers of thin, lexical-only critiques.

## What Changes

- Rebuild both few-shots so the demonstrated output *is* the stated bar: 5 genuine, non-overlapping suggestions in the backend example (up from 3), covering the declared priority categories — meaning loss / modality, systematic grammar, domain term, register, collocation — instead of three lexical/register items only.
- Remove padding-by-repetition from the WebLLM few-shot (the third item restated the first item's 史詩→叙事詩 point) and replace it with a distinct semantic-omission issue.
- Strip model-facing meta-instruction text out of few-shot `reason` strings so the examples model user-facing critique prose only.
- Demonstrate an omitted `sourceExcerpt` in the backend few-shot (a Japanese-internal grammar fault has no 原文 counterpart) so a filled-in excerpt on every item does not bias the model toward fabricating one.
- Add an explicit note that the example's item count reflects its two-sentence input and is not a cap, to counteract cardinality anchoring.
- Replace count-suppressing hedges with non-suppressing equivalents: drop `质量优先于条数` as a standalone license to under-report (keep the anti-fabrication rule it was attached to), and swap the global `宜简明` cue for a per-item length bound (2–4 sentences) that curbs bloat without curbing item count.
- Restructure the backend system prompt into labelled sections with coverage/count promoted out of the middle of a long prohibition paragraph, and de-duplicate the anti-label rule (it appeared four times across system prompt, few-shot preamble, user prompt, and retry nudge).
- Compress the duplicated coverage guidance in the WebLLM prompt so the 7B model gets each rule once.

Failover order (Gemini → Groq → Cloudflare), WebLLM's オフラインモード-only gating, provider timeouts, and the JSON response schema are unchanged. No suggestion-count cap exists anywhere in prompts, providers, or the parser (verified), so nothing needs removing there.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `ai-suggestions`: Few-shot exemplars must demonstrate the stated coverage density, the declared priority issue categories, non-overlapping distinct items, and an omitted `sourceExcerpt` case; prompt instruction text must not carry hedges that license under-reporting; rules must appear once at the appropriate level rather than being repeated across layers.

## Impact

- `backend/app/llm/prompts.py` (system prompt structure, few-shot, user-prompt reminder block)
- `frontend/src/lib/webllm/prompts/system.ts`, `frontend/src/lib/webllm/prompts/fewShot.ts` (kept in sync, compressed for Mistral 7B)
- `backend/app/llm/suggestions.py` (retry nudge de-duplication only)
- `backend/tests/test_llm_prompts.py`, `frontend/src/lib/webllm/__tests__/prompts.test.ts`, `backend/tests/fixtures/*`
- No API, DB, schema, failover, or secret changes
