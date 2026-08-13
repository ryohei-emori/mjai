## Why

Production `/api/suggestions` returns Vercel `504 FUNCTION_INVOCATION_TIMEOUT` because Gemini’s HTTP timeout (45s) and the Gemini→Groq→Cloudflare chain (plus parse retries) can exceed the serverless `maxDuration` (30s). Platform 504s hide useful 503 diagnostics (`gemini_pool_size`, etc.).

## What Changes

- Align provider HTTP timeouts and Vercel `maxDuration` so a single suggestions request fits the platform budget.
- Bound total suggestions wall-clock so the app returns a clear 503 before Vercel kills the function with 504.
- Keep empty Gemini pool as an immediate skip (no hang); document Gemini + Vercel timeout ops briefly in `AGENTS.md`.
- Confirm Production/Preview `GEMINI_API_KEYS` are set (ops; not committed).

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `ai-suggestion-generation`: Suggestions generation MUST finish within a wall-clock budget compatible with Vercel `maxDuration`, failing with HTTP 503 (not platform 504) when the budget is exhausted; Gemini MUST use an HTTP timeout that fits that budget; unconfigured Gemini MUST be skipped without waiting.

## Impact

- `vercel.json` (`api/index.py` `maxDuration`)
- `backend/app/llm/gemini_provider.py`, `cloudflare_provider.py`, `suggestions.py`, tests
- `AGENTS.md` (brief ops note)
- Vercel env already has `GEMINI_API_KEYS` (verify/redeploy only; no secrets in git)
