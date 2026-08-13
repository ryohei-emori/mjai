## 1. Key pool hardening

- [x] 1.1 Deduplicate credentials on load in `key_pool.py`; add pool-index helpers for safe logging
- [x] 1.2 Improve Groq/Cloudflare 429/cooldown exhaustion errors to include provider + pool size/index (no secrets)
- [x] 1.3 Surface clearer rate-limit/quota message on `POST /suggestions` 503 when all providers exhaust credentials
- [x] 1.4 Extend `test_key_pool.py` for dedupe, plural-not-merged-with-singular, and 429 next-key / all-exhausted behavior

## 2. Ops docs

- [x] 2.1 Add brief AGENTS.md note: pool spreads load; hard RPD/quota is per account; plural overrides singular (no double-count)
- [x] 2.2 Clarify `conf/.env.example` comments for plural vs singular (names/placeholders only)

## 3. Lazy WebLLM on frontend

- [x] 3.1 Extract WebLLM types / engineReady so `page.tsx` need not statically import `engine` / `@mlc-ai/web-llm`
- [x] 3.2 Change `page.tsx` generate flow to dynamic-import WebLLM only for オフラインモード or intentional API fallback
- [x] 3.3 Keep WebGPU check / diagnostics UI helpers on non-mlc modules
- [x] 3.4 Update frontend tests/mocks for lazy import paths

## 4. Shared saved proposals + error visibility + no auto-fallback

- [x] 4.1 Structured suggestion API errors (`rate_limited`, human `message`) in `api.ts`
- [x] 4.2 Remove API→WebLLM auto-fallback entirely; any cloud failure fails the job + toast (WebLLM only if offline toggle ON)
- [x] 4.3 Poll `loadSessionDetails` for open session; merge History by `historyId` (keep local unsaved rows)
- [x] 4.4 Job Queue UI note that unconfirmed jobs are device-local until save

## 5. Verification

- [x] 5.1 Run backend key-pool pytest
- [x] 5.2 Run relevant frontend jest tests
- [ ] 5.3 Commit + push (no secrets; leave unrelated OpenSpec changes alone)
