## Context

See proposal.md — Why. Existing stack already enforces Simplified Chinese for `reason`/`overallComment` via prompts + `has_non_chinese_reason()` retry (`enforce-chinese-suggestion-comments`). That path does **not** check semantic truthfulness or whether a critique explains **why**. User discovery: false 「缺少」 particle inventing (Case A) and location-only reasons without 为什么 (Case B). User clarification: **why in every 指摘コメント is a Spec MUST for all critique types**, not an optional particle-only polish.

## Goals / Non-Goals

**Goals:**

- Encode MUST: every `reason` includes what/where **and why the correction is necessary**.
- Encode anti-false-「缺少」 / prefer real meaning·grammar·fluency·spelling issues in prompts (backend + WebLLM sync).
- Deterministic fixtures + tests for Case A/B and prompt wording.
- Optional low-noise heuristic for weak location-only 「缺少」 reasons for regression; document if retry wiring is skipped.

**Non-Goals:**

- Full NLP semantic validation of Japanese correctness (too brittle / noisy for production retry).
- Changing API schema, DB, auth, Chinese-language detector, or unrelated changes (exemplar input, topbar bell, etc.).
- AGENTS.md / SYSTEM-DESIGN updates (prompt/fixture-only; no architecture change).

## Decisions

### 1. Prompt-first enforcement of MUST why-in-reason

**Choice:** Put the MUST in system (+ brief user reinforce) prompts in Simplified Chinese, synced across `backend/app/llm/prompts.py` and `frontend/src/lib/webllm/prompts/`. Few-shot examples must already include 为什么 so the model sees compliant shape.

**Rationale:** Generation quality is primarily prompt-driven; a hard semantic validator cannot reliably know whether 「は」 is truly needed.

**Alternatives:** Rely only on post-hoc filtering — rejected; too late and too noisy for Case A false positives.

### 2. Lightweight weak-reason heuristic — test/regression first; no retry by default

**Choice:** Add `has_weak_critique_reason(result)` (name flexible) in `parser.py` that flags Chinese reasons matching a narrow pattern: looks like 「缺少「…」在…」 (or close) **and** lacks any necessity cue (e.g. 因为 / 因此 / 必须 / 需要 / 用于 / 表示 / 才能 / 否则 / 才能 / 为了 / 语感 / 对比 / 强调 / 主题 / 才能听清 — keep a small allow-list of 为什么 markers). Use it in **unit tests + fixtures**; **do not** wire into `generate_suggestions()` retry loop in this change unless false-positive rate on existing good few-shot reasons is clearly zero.

**Rationale:** Spec MUST is about content quality; retrying on a brittle regex risks discarding good short Chinese reasons that use other wording. Prompt + fixtures carry the MUST; heuristic documents Case B for CI.

**Trade-off documented:** Hard validator in the retry loop is **deferred** as too noisy. If live smoke later shows persistent location-only 「缺少」, revisit wiring under a follow-up.

### 3. Fixtures for Case A / Case B

**Choice:** New module under `backend/tests/fixtures/` (e.g. `semantic_reason_cases.py`) holding:

- Case A: TARGET sentence `多くの芸人は文字を読むことができなかったが、長い詩を吟唱することができる` + documented bad reason `缺少「が」在「できなかった」后` (false inventing) + note that acceptable Japanese should not get that critique.
- Case B: sentence `彼らの語りは、演じる場所によって誰でもはっきり聞こえるとは限らない` + weak reason `缺少「は」在「誰でも」前` (fails why-required) + example compliant reason that includes 为什么.

Optional SOURCE excerpts if useful; not required for heuristic tests.

### 4. Keep Chinese enforcement orthogonal

**Choice:** Do not weaken or broaden `has_non_chinese_reason()`. New heuristic is separate and only about weak critique shape.

## Risks / Trade-offs

- **[Risk] Heuristic false positives on valid short Chinese reasons** → Mitigation: keep pattern narrow (缺少 + 在 + no necessity markers); tests for good reasons from existing few-shot; **no retry wiring** by default.
- **[Risk] Models still invent false 「缺少」 despite prompts** → Mitigation: fixtures + manual verify sentences; live smoke remains optional/out of CI.
- **[Risk] Prompt bloat for WebLLM token budget** → Mitigation: add 1–2 ultra-short Chinese rule lines, not long essays; mirror intent with backend.

## Migration Plan

- Deploy with normal frontend/backend release (prompt strings only + tests). No DB migration. Rollback = revert prompt/heuristic commits.
