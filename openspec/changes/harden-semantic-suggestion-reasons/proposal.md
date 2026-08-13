## Why

AI suggestions sometimes invent false particle critiques (e.g. 「缺少「が」…」 when the Japanese is already acceptable) or emit critique comments that only name the issue/location without explaining **why the fix is needed**. Users require semantically sound critiques, and every `reason`（指摘コメント）MUST include the necessity of the correction—not as an optional polish.

## What Changes

- Harden backend and WebLLM prompts so models prefer true meaning / grammar / fluency / spelling issues and **avoid inventing false 「缺少」 particle fixes** when Japanese is already acceptable.
- **MUST (spec-level):** Every suggestion `reason`（指摘コメント）MUST state (1) what is wrong / where, **and** (2) **why the correction is necessary** (为什么必须改 / 交际・语法上的必要性). This applies to **all** critique types, not only particle additions. Location-only patterns such as 「缺少「X」在…」 without 为什么 are non-compliant.
- Keep existing Simplified-Chinese enforcement for `reason`/`overallComment` and Japanese `original`/`sourceExcerpt` unchanged.
- Add deterministic fixtures + tests for Case A (false 「缺少「が」」 style) and Case B (weak reasons missing 为什么); optionally a lightweight heuristic for weak 「缺少」/location-only reasons if low-noise — document trade-offs if a hard retry validator would be too brittle.
- Do **not** change API schema, DB, auth, or unrelated OpenSpec work (e.g. exemplar translation input).

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `ai-suggestions`: Semantic-quality rules — no false particle inventing; **`reason` MUST include why the correction is needed** (all critique types); fixtures/heuristics support regression checks.

## Impact

- `backend/app/llm/prompts.py` — semantic quality + mandatory why-in-reason rules (+ few-shot if needed)
- `frontend/src/lib/webllm/prompts/` — keep in sync with backend
- `backend/app/llm/parser.py` — optional lightweight weak-reason heuristic (if adopted)
- `backend/app/llm/suggestions.py` — only if heuristic is wired into retry (decision in design)
- `backend/tests/fixtures/` — Case A/B corpora + bad/good reason examples
- `backend/tests/` — prompt content tests + heuristic/fixture assertions
- No AGENTS.md / SYSTEM-DESIGN updates unless architecture meaningfully changes (unlikely)
