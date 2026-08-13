## Context

See proposal.md — Why. Prior work in `refine-suggestion-card-interactions` added `has_non_chinese_reason()` (Hiragana/Katakana) wired into `generate_suggestions()`'s shared retry budget; `add-groq-cloudflare-suggestions` established field-level Chinese explanations vs Japanese `original`. Those changes are complete; Japanese still slips through via weak prompt framing and kana-only detection gaps (all-kanji Japanese comments). Exemplar/model-answer input is owned elsewhere — do not implement here.

## Goals / Non-Goals

**Goals:**
- Make Chinese for `reason`/`overallComment` the hard default via prompt + enforcement.
- Adopt the user's correction brief as primary task framing.
- Tighten detection carefully; keep MAX retry = 3; degrade gracefully.
- Keep backend/WebLLM prompt language rules aligned.

**Non-Goals:**
- Exemplar/model-answer UI or API fields.
- Full NLP / langdetect dependency.
- Distinguishing Simplified vs Traditional Chinese as a hard reject (Traditional may still pass if no Japanese signals).
- Changing suggestion card UI or persistence of `sourceExcerpt`.

## Decisions

### 1. New change (not reopen completed Chinese-enforcement changes)

**Choice:** Create `enforce-chinese-suggestion-comments` rather than reopen `refine-suggestion-card-interactions` or `add-groq-cloudflare-suggestions`.

**Rationale:** Both prior changes are complete and bundle unrelated UI/provider work. Expanding their intent would muddy archives. This change is a focused follow-up on language quality.

### 2. Task framing + stronger Chinese rules in prompts (backend + WebLLM)

**Choice:** Put 「意味の不一致、文法、流暢さ、スペルミスに焦点を当てて、この課題を添削してください。」 near the top of the system (and mirrored WebLLM) prompt as the primary task. Keep JSON schema / ≥5 / `sourceExcerpt` rules. Amplify language rules: `reason`/`overallComment` MUST be Simplified Chinese; forbid Japanese (including kana and Japanese prose) in those fields; `original`/`sourceExcerpt` stay Japanese. Keep few-shot demonstrating the split.

**Rationale:** Models follow salient task + language instructions; the previous Japanese-heavy system prompt biased explanations toward Japanese even when a field rule existed.

**Alternative:** Chinese-only entire system prompt. Rejected for cloud path — 原文/添削対象 are Japanese; prior full-Chinese port contributed to garbled `original`. Field-level split stays.

### 3. Stricter `has_non_chinese_reason()` without rejecting shared Hanzi Chinese

**Choice:** Expand detection to:
1. Hiragana / Katakana (existing ranges)
2. Halfwidth Katakana (U+FF66–U+FF9D)
3. Japanese particle/function-word patterns (e.g. です/ます/である/した/して/ない and common particles は/が/を/に/で as kana) via a compiled regex

Do **not** reject on Han-only text that looks like Simplified Chinese. Do **not** use “absence of Simplified-only characters” alone as a fail (too many false positives on short Chinese).

**Rationale:** Kana + JP function words are high-precision Japanese signals. All-kanji Japanese without those markers is rare in connective correction prose; prompts are the main mitigation for that edge case.

**Alternative:** langdetect / fastText. Rejected — dependency + weak on short strings.

### 4. Retry budget unchanged

**Choice:** Keep composing with JSON-parse failure under `MAX_PARSE_RETRY_ATTEMPTS` (3); return last result, never raise on language exhaustion.

### 5. WebLLM: matching prompts; minimal client detector

**Choice:** Update WebLLM `system.ts` / `fewShot.ts` (and templates only if needed for framing). Export a small `hasNonChineseReason()` in `frontend/src/lib/webllm/parser.ts` mirroring backend heuristics for tests / optional caller use. Full retry-loop parity in the WebLLM engine is nice-to-have only if a single small hook fits; do not large-refactor the offline pipeline.

### 6. 15-iteration verification harness (mocked for CI)

**Choice:** Add a backend test that runs **15 times** (loop or parametrize) over the enforcement path: each iteration asserts Chinese payloads pass `has_non_chinese_reason()` and Japanese payloads fail it, and/or that `generate_suggestions()` retries Japanese mock responses then accepts Chinese within the shared attempt budget. Live Groq smoke is `@pytest.mark.integration` and skipped without keys — CI must stay deterministic.

**Rationale:** Matches the product requirement 「毎回テストを１５回行い」 without flaky network dependence.

## Risks / Trade-offs

- **[Risk] False positive when Chinese `reason` quotes Japanese with kana** → Retry (accepted; same as prior change). Prefer clean Chinese explanations.
- **[Risk] All-kanji Japanese still slips through** → Mitigate primarily via stronger prompts; detector remains high-precision, not high-recall on pure Han.
- **[Risk] Prompt drift between backend and WebLLM** → Tasks require updating both and a light test/assert on shared phrases where practical.

## Migration Plan

Deploy via normal Vercel git path. No DB migration. Rollback = revert prompt/parser commit.
