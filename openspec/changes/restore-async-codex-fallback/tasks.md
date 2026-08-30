## 1. Frontend Transport Contract

- [x] 1.1 Add focused tests for async unconfigured, submission 5xx/network failure, malformed success, successful completion, and terminal 400/401/403 outcomes.
- [x] 1.2 Add polling tests for pending-to-completed, recoverable 404/5xx/network failure, malformed status, and polling deadline fallback using fake timers.
- [x] 1.3 Update existing suggestion API and component fetch mocks so they explicitly model the async preflight before synchronous success or failure.

## 2. Frontend Fallback Implementation

- [x] 2.1 Extract async Codex submission and polling into a response classifier that distinguishes completed, recoverable, and terminal outcomes.
- [x] 2.2 Route every recoverable async outcome to the existing synchronous `/suggestions` request while preserving authentication handling and structured cloud failure diagnostics.
- [x] 2.3 Verify that successful async completion never calls the synchronous endpoint and terminal client/authentication failures never trigger fallback.

## 3. API Base Normalization

- [x] 3.1 Add a pure API-base resolver with tests for whitespace, trailing slashes, empty production values, and empty development values.
- [x] 3.2 Use the normalized base for all frontend API calls and remove the unconditional production localhost fallback from Next configuration.
- [x] 3.3 Build the production frontend and verify the bundle contains neither `/api\n` nor a production `localhost:8000` API base.

## 4. Backend Async Endpoint Contract

- [x] 4.1 Add endpoint tests for missing required text, unconfigured Codex gateway, failed configured-gateway submission, pending task acceptance, pending polling, completed polling, and failed polling.
- [x] 4.2 Add non-sensitive server logging for async submission and polling failures so the upstream reason is observable in Vercel logs.

## 5. Verification

- [x] 5.1 Run focused frontend and backend contract tests and resolve all failures caused by the change.
- [x] 5.2 Run the complete frontend Jest suite and backend pytest suite with no regressions.
- [x] 5.3 Run OpenSpec strict validation for `restore-async-codex-fallback` and confirm every implementation task is complete.
