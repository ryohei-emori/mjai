## Context

See `proposal.md` for the production failure. The frontend currently owns transport selection: it always calls the async endpoint first and only treats HTTP 404 as permission to call the synchronous endpoint. The backend returns HTTP 502 when a configured Codex gateway cannot accept or report a task, while the synchronous generator already catches Codex provider errors and continues to Gemini, Groq, and Cloudflare.

The two browser calls carry the same authenticated request body. Async generation itself does not persist a correction history, so starting the synchronous fallback does not duplicate application records, although an already accepted remote Codex task can continue consuming remote compute.

## Goals / Non-Goals

**Goals:**

- Make the optional async Codex path obey the provider-failover contract.
- Keep authentication and input failures terminal.
- Make response-state handling explicit and independently testable.
- Normalize the API base consistently for generic and suggestion-specific calls.
- Restore the complete frontend test suite after the async transport change.

**Non-Goals:**

- Repair or operate the private Codex gateway itself.
- Change provider preference after Codex fallback (Gemini remains ahead of Groq and Cloudflare).
- Add cancellation to the remote Codex task API.
- Implement the separate future specification mentioned by the user.

## Decisions

### Classify async outcomes before choosing fallback

The frontend will centralize async submission/polling into a helper that yields either a completed response, a terminal error, or a recoverable failure. Recoverable failures include network errors, 404, 5xx responses, invalid successful response shapes, missing tasks during polling, and the client polling deadline. The caller then invokes the existing synchronous `/suggestions` path.

This keeps the long-running task protocol in the browser without duplicating the Gemini/Groq/Cloudflare orchestration in the async backend endpoint. Returning 404 for every gateway failure was considered, but rejected because it erases useful endpoint semantics and makes operational diagnosis harder.

### Preserve terminal 4xx responses

HTTP 400, 401, and 403 remain terminal. Retrying the same invalid or unauthenticated body against `/suggestions` cannot succeed and could obscure forced-sign-out behavior. An async polling 404 is recoverable because it represents lost task state rather than an invalid original suggestion request.

### Let the synchronous chain own the final failure diagnostics

After a recoverable Codex failure, a successful cloud response is returned normally. If the cloud chain also fails, its structured 503 body becomes the final client error because it describes every remaining configured provider and the available offline fallback. The original Codex failure remains suitable for server logging but does not replace the more actionable chain result.

### Normalize the API base once

A small pure resolver will trim the configured value and trailing slashes. It will choose `/api` for an empty production value and `http://localhost:8000` for an empty development/test value. The Next configuration will stop baking an unconditional localhost fallback into production bundles. Pure resolver tests avoid depending on build-time environment mutation.

### Test each transport transition, not only final UI messages

Dedicated frontend API tests will assert the URL sequence, request body, authorization header, and final result/error for each async state. Existing component tests may share a mock helper that answers the async preflight consistently before the response they actually intend to exercise. Backend endpoint tests will mock the gateway boundary and assert 404, 502, pending, and completed shapes without making external calls.

## Risks / Trade-offs

- **[An accepted remote task can finish after polling fails and cloud fallback starts]** → No app history is written by the remote task alone; document the possible compute duplication and leave cancellation for a future gateway protocol change.
- **[Falling back after the polling deadline increases total user-visible latency]** → Preserve the existing background job UI and test the deadline path with fake timers; a successful fallback is preferable to a terminal gateway error.
- **[Over-broad fallback could mask authentication failures]** → Use an explicit terminal status allowlist and tests asserting that `/suggestions` is not called for 400/401/403.
- **[Changing API-base defaults can affect local tests]** → Keep localhost as the non-production default and test both environments through the pure resolver.

## Migration Plan

1. Add the resolver and async-transport contract tests so the current behavior fails deterministically.
2. Implement recoverable fallback and update existing fetch mocks.
3. Add backend async endpoint contract tests and any minimal logging needed for the gateway failure reason.
4. Run focused suites, then the complete frontend and backend suites, and build the production frontend to verify that no `/api\n` or production localhost base is embedded.
5. Deploy normally through Vercel Git integration and confirm `/api/suggestions/async` failures are followed by `/api/suggestions` requests in runtime logs.

Rollback is a code rollback; no schema or persisted-data migration is involved.
