## Why

AI suggestion `reason` and `overallComment` fields are still often emitted in Japanese despite existing prompt rules and a Hiragana/Katakana retry check. Recipients are Chinese speakers, so those explanatory fields MUST be Simplified Chinese. Kana-only detection also misses some all-kanji Japanese comments. The prompt's task framing should match the reviewer's actual brief (meaning mismatch, grammar, fluency, spelling).

## What Changes

- Strengthen backend and WebLLM prompts so Chinese for `reason`/`overallComment` is unmistakable and hard to violate, while `original` (flagged TARGET TEXT) and `sourceExcerpt` stay Japanese as today.
- Reframe the core user-facing correction task around: 「意味の不一致、文法、流暢さ、スペルミスに焦点を当てて、この課題を添削してください。」 as primary task instruction (not a side comment), keeping the existing JSON schema (`suggestions` with `original`/`reason`/`sourceExcerpt`, `overallComment`, ≥5 suggestions target).
- Tighten `has_non_chinese_reason()` heuristics (kana + careful Japanese particle/pattern signals) without rejecting legitimate Simplified Chinese that shares Han characters; keep retry up to existing `MAX_PARSE_RETRY_ATTEMPTS` (3) on language failure.
- Mirror prompt language rules on the WebLLM path; add minimal client-side language detection if feasible without a large refactor.
- Add/extend backend tests for detection, retry, and prompt expectations.
- Add a **15-iteration** verification test under `backend/tests/` that repeatedly exercises the enforcement detector / retry path so `reason`/`overallComment` pass as fully Chinese (mocked LLM responses for CI stability; optional live smoke skipped without API keys).

**Out of scope:** exemplar/model-answer input field (owned by a separate change).

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `ai-suggestions`: Strengthen bilingual field-language requirements (Chinese explanations), primary task framing, and stricter non-Chinese detection + retry behavior for `reason`/`overallComment`.

## Impact

- `backend/app/llm/prompts.py` — system/user prompt framing and language rules
- `backend/app/llm/parser.py` — `has_non_chinese_reason()` heuristics
- `backend/app/llm/suggestions.py` — retry loop unchanged in budget; consumes stricter detector
- `frontend/src/lib/webllm/prompts/*` — matching prompt wording
- `frontend/src/lib/webllm/parser.ts` (optional minimal mirror of language check)
- `backend/tests/test_llm_parser.py`, `backend/tests/test_llm_suggestions.py` (+ prompt tests as needed)
- No API contract / DB / auth changes
