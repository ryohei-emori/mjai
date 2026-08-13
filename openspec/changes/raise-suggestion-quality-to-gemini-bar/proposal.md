## Why

After `harden-semantic-suggestion-reasons`, critiques are Chinese, accessible, and less inventively wrong — but still lag Gemini-style quality: constructive overall framing, concrete `現状 → 推奨` replacements, domain-aware CN→JP literary/academic register advice, and dense multi-issue coverage. Users want that quality bar on Groq/Cloudflare/WebLLM (prompt+schema), without reintroducing Gemini as a provider.

## What Changes

- Teach prompts (backend + WebLLM sync) Gemini-like critique shape: `overallComment` strengths-then-gaps; each `reason` as `問題/現状 → 推奨修正（読み仮名任意）` + plain Chinese why.
- Domain framing: CN→JP literary/academic essay translation critique (epic/oral-literature terms, register, calque, sense modality, etc.).
- Keep schema `original` + `reason` + optional `sourceExcerpt` — put `現状 → 推奨` inside `reason` (no API/DB expansion).
- Reconcile quote policy: allow Japanese corner brackets 「」 **only** when citing Japanese TARGET words/phrases; Chinese meta-prose MUST use `""` / `“”`. Narrow `has_japanese_corner_quotes_in_critique` so legitimate JP cites do not over-retry.
- Expand few-shot with 1–2 short Gemini-shaped Chinese examples.
- Add fixture documentation of the quality bar (e.g. `gemini_quality_bar_cases.py` and/or extend `semantic_reason_cases.py`); no live LLM in CI.
- Do **not** touch `add-optional-exemplar-translation-input` or reintroduce Gemini provider keys.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `ai-suggestions`: Gemini-quality critique structure (overallComment + per-reason shape), CN→JP literary/academic domain guidance, revised quote-mark policy (「」 only for JP cites), narrowed corner-quote retry heuristic, quality-bar fixtures/prompt tests.

## Impact

- `backend/app/llm/prompts.py` — system/few-shot/user reinforce for structure + domain + quote policy
- `frontend/src/lib/webllm/prompts/{system,fewShot}.ts` (+ templates only if needed) — sync
- `backend/app/llm/parser.py` — narrow corner-quote misuse heuristic; `suggestions.py` reinforce line if still absolute-forbid 「」
- `backend/tests/fixtures/` — quality-bar corpora / desired critique shapes
- `backend/tests/test_llm_prompts.py`, `test_llm_parser.py` + frontend Jest prompt tests
- No AGENTS.md / SYSTEM-DESIGN unless architecture changes (unlikely); no Gemini provider
