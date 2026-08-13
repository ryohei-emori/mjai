## Context

See proposal.md — Why. Existing stack already enforces Simplified Chinese for `reason`/`overallComment` via prompts + `has_non_chinese_reason()` retry (`enforce-chinese-suggestion-comments`), and prior work in this change added MUST why-in-reason + anti-false-缺少 + `has_weak_critique_reason()` (test-only). New user feedback adds: accessible plain-Chinese why, Chinese double quotes (never 「」), accurate SOURCE citation, multi-paragraph coverage, and another meaning/wording drift case.

## Goals / Non-Goals

**Goals:**

- Encode MUST: every `reason` includes what/where **and why**, in plain Chinese accessible without JP↔CN craft knowledge.
- Encode MUST: Chinese critique fields use `""` / `“”`, never 「」.
- Encode prompt rules: accurate SOURCE citation; no inventing/misquote; no drift rewrites; multi-paragraph coverage guidance; keep anti-false-缺少.
- Sync backend + WebLLM prompts; extend fixtures/tests (Case A/B + Case C meaning/wording + quote/accessibility assertions).
- Optional low-noise 「」 heuristic; wire to retry only if clearly safe.

**Non-Goals:**

- Full NLP semantic validation of Japanese/SOURCE correctness (too brittle for production retry).
- Changing API schema, DB, auth, or unrelated changes (`add-optional-exemplar-translation-input`, etc.).
- AGENTS.md / SYSTEM-DESIGN updates (prompt/fixture-focused; no architecture change).

## Decisions

### 1. Prompt-first for accessibility, SOURCE fidelity, coverage

**Choice:** Add short Simplified-Chinese MUST/guidance lines to system (+ brief user reinforce) in `backend/app/llm/prompts.py` and sync ultra-short equivalents in WebLLM `system.ts` / `fewShot.ts`. Few-shot citations switch from 「」 to `""`.

**Rationale:** Generation quality remains prompt-driven; semantic truthfulness cannot be hard-validated reliably.

### 2. Quote-mark style: `""` / `“”` only in Chinese fields

**Choice:** Prompts forbid 「」 inside `reason`/`overallComment`. Update `_strip_quoted_japanese_spans` to also strip ASCII `"`…`"` and Unicode `“`…`”` so Chinese-language detection still allows JP form cites under the new style. Keep stripping 「」 for backward compatibility with older model outputs during transition.

**Rationale:** User feedback: 「」 are not Chinese quotation marks. Few-shot must demonstrate `""`.

### 3. 「」 in Chinese fields — low-noise retry OK

**Choice:** Add `has_japanese_corner_quotes_in_critique(result)` that returns True if any `reason` or `overallComment` contains 「 or 」. Wire into `generate_suggestions()` retry composition alongside `has_non_chinese_reason` (same attempt budget). Document that weak-缺少 heuristic stays test-only.

**Rationale:** Presence of corner brackets in Chinese critique fields is deterministic and low-noise after the prompt forbid — safe like the Chinese check. Weak location-only 缺少 remains too wording-dependent for retry.

### 4. Weak-reason heuristic — keep test-only; accept `""` form

**Choice:** Extend `_WEAK_QUE_SHAO_LOCATION` to match `缺少"X"在` and `缺少“X”在` as well as legacy `缺少「X」在`. Still **not** wired into retry.

### 5. Fixtures

**Choice:** Extend `semantic_reason_cases.py`:

- Case A/B: update example strings to preferred `""` style (keep notes that legacy 「」 forms are also weak/bad).
- Case C: TARGET-like epic wording issue (`歴史物語による常套語は…シナリオを覚えないのだ`) + documented weak/wrong reason that drifts toward 「听众一听就知道大概，不会落下剧情」 without accurate meaning why.
- Case D (optional metadata): meaning-mismatch misquote pattern (invented SOURCE paraphrase) for documentation/manual verify.

## Risks / Trade-offs

- **[Risk] Models still emit 「」 from habit** → Mitigation: few-shot uses `""`; retry on corner brackets; prompt MUST.
- **[Risk] Stripping `"` too aggressively breaks Chinese detection** → Mitigation: only strip paired quote spans; keep kana/function checks on remaining prose.
- **[Risk] Prompt bloat for WebLLM** → Mitigation: ultra-short Chinese rule lines; mirror intent with backend.
- **[Risk] Coverage guidance causes spam critiques** → Mitigation: prompt says quality over spam / no inventing.

## Migration Plan

- Deploy with normal frontend/backend release (prompts + parser heuristic + tests). No DB migration. Rollback = revert those commits.
