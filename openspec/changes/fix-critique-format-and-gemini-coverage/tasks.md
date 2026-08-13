## 1. Prompts (natural prose + coverage)

- [x] 1.1 Update `backend/app/llm/prompts.py`: forbid spoken `现状：`/`推荐：`/`現状：`/`推奨：` prefixes; keep problem→fix→why + teaching bar in natural Chinese; strengthen multi-paragraph density (≥5 when real issues exist, do not stop after 1–2); revise schema example / user nudge strings accordingly.
- [x] 1.2 Sync `frontend/src/lib/webllm/prompts/system.ts` and `fewShot.ts` with the same natural-prose + coverage guidance; ensure few-shots do not train colon-labeled templates.
- [x] 1.3 Update `LANGUAGE_RETRY_NUDGE` (and related nudge text) in `backend/app/llm/suggestions.py` so retries do not re-teach rigid `现状→推荐` spoken labels.

## 2. Gemini output headroom

- [x] 2.1 Raise Gemini `generationConfig.maxOutputTokens` to at least 8192 in `gemini_provider.py`.
- [x] 2.2 Log candidate `finishReason` when present (especially truncation / `MAX_TOKENS`) without logging secrets.

## 3. Tests and fixtures

- [x] 3.1 Update backend prompt tests: assert anti-label guidance + coverage/density cues; stop requiring colon-labeled `现状：` as the reason shape MUST.
- [x] 3.2 Update WebLLM prompt tests similarly.
- [x] 3.3 Assert Gemini payload `maxOutputTokens >= 8192`; adjust quality-bar / teaching fixture comments if they mandate spoken label prefixes as the only compliant shape.
- [x] 3.4 Run focused backend + frontend prompt/Gemini unit tests and fix regressions.

## 4. Docs touch (ops truth)

- [x] 4.1 If AGENTS.md / SYSTEM-DESIGN mention mandatory `現状 → 推奨` spoken shape, soften to natural prose problem→fix→why without requiring those colon labels (failover order unchanged).
