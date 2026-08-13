## Why

AI suggestions sometimes invent false particle critiques, omit **why** a fix is needed, misquote SOURCE when claiming meaning mismatch, use Japanese corner brackets 「」 inside Chinese critique prose, pile critiques on one paragraph, or write reasons only a JP↔CN translation specialist would understand. Users need semantically sound, accessible Simplified-Chinese critiques with accurate SOURCE citation and broader paragraph coverage.

## What Changes

- Harden backend and WebLLM prompts so models prefer true meaning / grammar / fluency / spelling issues and **avoid inventing false 「缺少」 particle fixes** when Japanese is already acceptable.
- **MUST (spec-level):** Every suggestion `reason`（指摘コメント）MUST state (1) what is wrong / where, **and** (2) **why the correction is necessary**, in plain Chinese understandable to a reader who does **not** know Japanese↔Chinese translation craft (no JP linguistics jargon assumption; do not assume the reader can read Japanese). Applies to **all** critique types. Location-only patterns such as `缺少"X"在…` without 为什么 are non-compliant.
- **MUST:** Chinese critique text (`reason` / `overallComment`) uses ASCII/Chinese double quotes (`""` / `“”`), **never** Japanese corner brackets 「」.
- **MUST (prompt):** When citing SOURCE for meaning mismatch, do not invent/misquote; quote accurately and explain the mismatch clearly; when critiquing awkward JP wording vs SOURCE meaning, explain the meaning problem accurately and avoid rewrite suggestions that drift from SOURCE.
- **Guidance (prompt):** For multi-paragraph TARGET, aim to surface real issues across paragraphs (systematic coverage; quality over spam; no invented issues).
- Keep existing Simplified-Chinese enforcement for `reason`/`overallComment` and Japanese `original`/`sourceExcerpt` unchanged (except citation-quote style inside Chinese fields).
- Extend fixtures/tests: Case A/B retained; add meaning-fidelity / accessibility / quote-mark cases; optional low-noise 「」 heuristic — wire to retry only if clearly safe.
- Do **not** change API schema, DB, auth, or unrelated OpenSpec work (e.g. `add-optional-exemplar-translation-input`).

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `ai-suggestions`: Semantic-quality rules — no false particle inventing; **`reason` MUST include accessible why**; Chinese double quotes only; accurate SOURCE citation; multi-paragraph coverage guidance; fixtures/heuristics support regression checks.

## Impact

- `backend/app/llm/prompts.py` — semantic quality, accessibility, quote marks, SOURCE fidelity, paragraph coverage (+ few-shot sync)
- `frontend/src/lib/webllm/prompts/` — keep in sync with backend
- `backend/app/llm/parser.py` — weak-reason heuristic; strip `""`/`“”` for Chinese checks; optional 「」 detection
- `backend/app/llm/suggestions.py` — only if 「」 heuristic is wired into retry (decision in design)
- `backend/tests/fixtures/` — Case A/B/C corpora + bad/good reason examples
- `backend/tests/` + frontend Jest prompt tests — prompt content + heuristic assertions
- No AGENTS.md / SYSTEM-DESIGN updates unless architecture meaningfully changes (unlikely)
