## Why

Operators saw “quota exceeded” after enabling a multi-key pool and could not see that failure in the MJAI UI. Separately, when one browser/environment saves AI proposals to the shared Supabase DB, another client on the same session does not see them in the right pane. Cloud suggestion generation also still risked loading WebLLM on the default API path.

## What Changes

- Document honest root causes: key-pool cooldown is process-memory-only; right-pane Job Queue / pre-confirm suggestions are **client-local** (React + localStorage); saved `ai_proposals` are DB-backed but the UI only loads them on session switch (no polling).
- Poll/refresh session histories + proposals while a session is open so **saved** proposals appear on other clients/environments sharing the DB.
- Surface cloud API failures (429/quota, 503, network, etc.) in toast + failed job state.
- **Never auto-fallback to WebLLM** unless オフラインモード is explicitly ON; remove the former API-failure→WebLLM path.
- Harden key pool (dedupe, index logs, clearer exhaustion errors) + AGENTS.md quota-vs-pool note.
- Lazy-load WebLLM only when offline mode is ON.

## Capabilities

### New Capabilities

- (none — observability of pool cooldown DB panel deferred; proposal sync + error visibility take priority)

### Modified Capabilities

- `ai-suggestion-generation`: Clearer rate-limit/quota 503 payloads; pool must not double-count env keys.
- `correction-workspace-ui`: Poll shared saved proposals into the right-pane History; visible cloud errors; WebLLM only when offline toggle is ON (no auto-fallback).

## Impact

- Frontend: `page.tsx` (poll, error handling), `api.ts` (structured suggestion errors).
- Backend: key pool / suggestions 503 messages (already started); tests.
- Docs: AGENTS.md, OpenSpec design verdict.
- Do not touch `add-optional-exemplar-translation-input`.
