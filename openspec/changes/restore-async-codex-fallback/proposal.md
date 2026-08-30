## Why

The browser now submits every cloud suggestion request to the optional Codex CLI async endpoint first, but a configured-yet-unavailable Codex gateway returns HTTP 502 and stops the request instead of falling back to the established Gemini → Groq → Cloudflare chain. Production logs show repeated async 502 responses while the rest of the API remains healthy, so the provider failover contract must cover async submission and polling failures explicitly.

## What Changes

- Treat recoverable Codex async submission and polling failures as provider failures and continue through the synchronous cloud-provider chain.
- Preserve terminal client/authentication errors instead of hiding them behind fallback.
- Add frontend contract tests for unavailable, failed, malformed, and successful async responses, including the existing optional-exemplar request shape.
- Add backend endpoint tests that distinguish an unconfigured Codex gateway from a configured gateway whose submission fails.
- Correct the production API-base handling so whitespace is removed and a production-empty value resolves to same-origin `/api` rather than localhost.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ai-suggestion-generation`: Extend provider failover requirements to the optional Codex CLI async transport, including submission/polling failures and same-origin production routing.

## Impact

- Frontend suggestion transport and API-base resolution in `frontend/src/app/api.ts` and `frontend/next.config.js`.
- FastAPI async suggestion endpoints and their tests.
- Frontend Jest mocks that currently assume the first request is always synchronous `/suggestions`.
- No database migration and no public request/response breaking change.
