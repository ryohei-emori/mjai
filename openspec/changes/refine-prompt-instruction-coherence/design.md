## Context

Eight successive changes layered rules onto one shared prompt pair (`backend/app/llm/prompts.py` and `frontend/src/lib/webllm/prompts/*`). Each layer added instruction text; none revisited the few-shot exemplars, which have stayed at three items since `raise-suggestion-quality-to-gemini-bar`. The immediately preceding change (`fix-critique-format-and-gemini-coverage`) raised Gemini's `maxOutputTokens` to 8192 and added explicit "do not stop after 1–2 items" text, which removes the output-budget and instruction-text explanations for thin critiques. What remains untested is the exemplars themselves.

## Audit findings

The thirteen accumulated requirements are all present as instruction text in both the backend and WebLLM prompts, and the two are in sync. The problems are in exemplars and hedges:

| # | Finding | Why it matters |
|---|---|---|
| 1 | Both few-shots show 3 suggestions while rules demand ≥5 | Demonstrated cardinality is a stronger signal than a numeric instruction; the example, not the rule, sets the model's expected item count |
| 2 | Few-shots show only lexical-substitution and register issues | The prompt declares meaning divergence, systematic grammar, and modality highest priority, but never demonstrates them, so the model imitates the lower-priority categories it can see |
| 3 | WebLLM few-shot item 3 restates item 1's 史詩→叙事詩 point | The prompt forbids padding by repetition, and the example does exactly that |
| 4 | Backend few-shot item 3's `reason` ends with a directive to the model (`不要主推删掉「紙に」之类表面省略`) | Trains the model to write model-facing meta-commentary into text the learner reads |
| 5 | All three backend few-shot items carry `sourceExcerpt` | Biases toward always emitting one, against the explicit "omit rather than fabricate" rule |
| 6 | `质量优先于条数` sits in the same sentence as the coverage MUST | Reads as permission to return few items; anti-fabrication and under-reporting get conflated |
| 7 | `reason/overallComment 宜简明完整` is a global brevity cue | Suppresses length and, with it, item count; a per-item bound achieves the anti-bloat intent without the side effect |
| 8 | The anti-label rule appears four times (system prompt, few-shot preamble, user reminder, retry nudge) | Token cost and dilution; repeated mention of a forbidden string also raises its salience |
| 9 | Coverage/count MUSTs are buried mid-paragraph in a ~30-prohibition block | Structural burial of the requirement most often violated |
| 10 | WebLLM prompt states the coverage rule and anti-padding clause twice | Wastes the limited instruction budget of a 7B model |

Verified as *not* a cause: there is no suggestion-count cap anywhere in `backend/app/llm/` (no fixed slice in the parser, providers, or `suggestions.py`).

## Goals / Non-Goals

Goals:
- Make the exemplars demonstrate the bar the rules state, in both count and issue category.
- Remove instruction text whose side effect is fewer or shorter items, without weakening anti-fabrication.
- Keep the backend and WebLLM prompts synced, and keep the WebLLM prompt small enough for Mistral 7B.

Non-Goals:
- Changing failover order, provider timeouts, `maxOutputTokens`, or the wall-clock budget.
- Reviving automatic WebLLM fallback (offline mode stays opt-in).
- Changing the JSON response schema or any API/DB contract.
- Loosening the Chinese-only rules for `reason`/`overallComment`, which are live-verified and intentionally repeated.

## Decisions

**Rebuild the backend few-shot to five items on the existing two-sentence corpus.** The corpus genuinely contains five distinct faults, so demonstrating five is honest rather than padded: 史詩 (domain term), でも (register), 紙に印する文字 (collocation), 経験は…読む (subject–predicate breakdown, no SOURCE counterpart), and the dropped 大概 (lost 推量 modality). This simultaneously fixes findings 1, 2, and 5 — the grammar item is the one that legitimately omits `sourceExcerpt`.

Alternative considered and rejected: keeping three items and relying on stronger numeric instruction. The preceding change already tried the instruction-text route; adding more text without fixing the exemplar repeats it.

**Add a one-clause note that the example count tracks the example input.** Cheap insurance against the model reading "5" as a target for all inputs, and against reading a short example as licence for a short answer on a long one.

**Replace the two count-suppressing phrasings rather than delete their intent.** `质量优先于条数` becomes an explicit statement that the anti-fabrication rule is not a reason to omit real issues; the global `简明` cue becomes a per-item bound of roughly two to four sentences, which keeps the anti-bloat purpose while removing the pressure to shorten the list.

**Reorganise the backend system prompt into labelled sections** (language rules / critique content / teaching priorities / coverage and output) so the coverage requirement occupies its own final block instead of the tail of a long prohibition paragraph. Rule content is preserved verbatim where possible so this stays a restructuring, not a rewrite.

**Drop the anti-label reminder from the few-shot preamble only.** The system prompt and the per-request reminder keep it; the retry nudge keeps it because that is the path where the failure was actually observed. The example itself now demonstrates compliant prose, which is the more reliable signal.

**Be additive-minimal on the WebLLM side.** Mistral 7B degrades with long instructions, so the WebLLM change is net-neutral or shorter: merge the duplicated coverage lines, fix the repeated few-shot item, add the count note, and add one grammar/modality exemplar — no new rule prose.

## Risks / Trade-offs

- A five-item example on a two-sentence input could suggest that short inputs always warrant five items. Mitigated by the explicit note and by the retained "return only what is real" rule.
- Longer few-shot means more input tokens per request (roughly 150–200), which slightly raises latency and input cost. It does not compete with `maxOutputTokens`, which governs output only, so the suggestion body's budget is unaffected.
- Restructuring the system prompt risks losing a substring some test asserts. Mitigated by running the deterministic prompt tests, which assert the presence of each rule's key wording.

## Verification

- `backend/tests/test_llm_prompts.py` and `frontend/src/lib/webllm/__tests__/prompts.test.ts` cover rule presence, few-shot shape, and the anti-pattern exclusions; extend them for the new exemplar requirements (item count, omitted `sourceExcerpt`, no duplicate-point item, no model-facing directive).
- A small live probe on the epic CN→JP corpus via the existing `backend/scripts/live_chinese_15x.py` harness, before and after, comparing `n_suggestions`. Kept to a few iterations to limit free-tier quota use; not part of CI, which must never call a live LLM.
