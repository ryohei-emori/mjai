## Context

See proposal.md — Why. Prior changes (`raise-suggestion-quality-to-gemini-bar`, `improve-suggestion-teaching-quality`) correctly required problem → fix → why and contrastive teaching, but encoded that as `现状 → 推荐` / `現状 → 推奨` schema language. Models (especially Gemini) copy that into spoken `现状：…推荐：…` (or JP `現状：`) prefixes. Coverage already says “目标至少 5 条” and “多段覆盖”, yet few-shots show only 2–3 items and Gemini `maxOutputTokens: 4096` can truncate dense multi-reason JSON — the parser then keeps the first complete suggestions (~2). Failover remains Gemini → Groq → Cloudflare (`reorder-llm-failover-gemini-first`); do not revert.

## Goals / Non-Goals

**Goals:**
- Natural Chinese `reason` prose with the same pedagogical content, without mandatory colon labels.
- Broader real-issue coverage on multi-paragraph TARGET via prompt density cues + Gemini output headroom.
- Keep backend ↔ WebLLM prompt sync and deterministic CI assertions (no live LLM).

**Non-Goals:**
- Changing failover order, schema fields, DB, or UI.
- Hard-failing post-parse if a model still emits `现状：` (prompt/test surface only for this change).
- Guaranteeing exactly N suggestions on every corpus (truthfulness still beats padding).

## Decisions

1. **Content vs spoken shape**
   - Keep MUST: state current problem, recommended JP form when clear, accessible why (+ contrastive nuance for lexical upgrades).
   - Explicitly forbid requiring spoken prefixes `现状：` / `推荐：` / `現状：` / `推奨：`.
   - Prefer teaching `旧形 → 「新形」：自然中文为什么…` as an allowed contrastive idiom inside prose, not as a labeled checklist.
   - Alternatives considered: post-parse strip of `现状：` — rejected (fragile, hides prompt bug); keep label MUST — rejected (user complaint).

2. **Prompt + few-shot sync**
   - Edit `backend/app/llm/prompts.py` and WebLLM `system.ts` / `fewShot.ts` together.
   - Schema example string must not say `现状 → 推荐` as the only reason template; describe natural Chinese with problem/fix/why.
   - Backend few-shot already uses flowing `A → 「B」：…` — keep that style; ensure comments/tests no longer require colon labels.
   - Strengthen coverage: “勿在仅找出1–2条后停止”; reinforce ≥5 when real issues exist; multi-paragraph scan.
   - Update `LANGUAGE_RETRY_NUDGE` in `suggestions.py` so retries do not re-teach `现状→推荐` labels.

3. **Gemini token budget**
   - Raise `generationConfig.maxOutputTokens` from 4096 → **8192**.
   - In `_extract_text_from_response` (or caller), log `candidates[0].finishReason` when present, especially `MAX_TOKENS`.
   - Alternatives: only prompt changes — insufficient if truncation is the bottleneck; 16384 — deferred (latency/cost; 8192 is enough for ~5–10 dense reasons).

4. **Tests**
   - Assert prompts contain anti-label guidance and coverage/density cues.
   - Assert Gemini payload `maxOutputTokens >= 8192`.
   - Loosen assertions that currently require the substring `现状` as a hard MUST for the reason shape (allow `→` / problem-fix-why wording instead).
   - Update fixture comments that mandate spoken `現状 → 推奨` labels as the only compliant shape.

## Risks / Trade-offs

- **[Risk] Models still emit labels from prior RLHF habits** → Mitigation: few-shot + explicit forbid + retry nudge rewrite; optional later post-process out of scope.
- **[Risk] Higher maxOutputTokens increases worst-case latency** → Mitigation: JSON mime type unchanged; timeout stays 45s; typical responses still shorter.
- **[Risk] Stronger “≥5” cue causes padding** → Mitigation: keep “禁止编造凑数 / 质量优先” wording from teaching bar.
- **[Risk] Truncation salvage still yields 2 items if model writes extremely long reasons** → Mitigation: 8192 + “简明完整、勿灌水”; monitor finishReason logs.

## Migration Plan

1. Ship prompt + Gemini config + tests together.
2. Redeploy Vercel (no new env vars).
3. Rollback: revert commit; failover order unaffected.

## Open Questions

- None for this change. If production still truncates after 8192, revisit token budget in a follow-up.
