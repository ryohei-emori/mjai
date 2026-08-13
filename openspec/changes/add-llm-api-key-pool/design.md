## Context

Today `groq_provider.py` and `cloudflare_provider.py` each read a single credential from env (`GROQ_API_KEY`; `CLOUDFLARE_ACCOUNT_ID` + `CLOUDFLARE_API_TOKEN`). Suggestion generation already rotates **models** within Groq and fails over Groq → Cloudflare → WebLLM, but a single rate-limited or revoked **account** still blocks that provider. See proposal.md for motivation. Vercel serverless is mostly stateless per invocation, so in-process cooldown is best-effort within a warm instance and resets on cold start.

## Goals / Non-Goals

**Goals:**
- One shared pool abstraction used by both providers for load + select + cooldown + in-provider key retry.
- Env-driven growth: add keys without code changes.
- Keep single-key production config working with zero Vercel changes.
- Unit-testable selection/cooldown/fallback without real network calls.

**Non-Goals:**
- Persistent cross-instance cooldown store (Redis, etc.).
- Changing the public `/api/suggestions` JSON contract.
- Rotating models and keys in one combined policy beyond “select key, then existing model rotation.”
- Auto-discovering Cloudflare account IDs at runtime in production (discovery is a one-time local setup aid only).

## Decisions

### 1. Env convention

| Provider | Plural | Singular (back-compat) |
|----------|--------|------------------------|
| Groq | `GROQ_API_KEYS=key1,key2` | `GROQ_API_KEY` |
| Cloudflare | `CLOUDFLARE_ACCOUNT_IDS=id1,id2` + `CLOUDFLARE_API_TOKENS=tok1,tok2` (same length) | `CLOUDFLARE_ACCOUNT_ID` + `CLOUDFLARE_API_TOKEN` |

**Merge rule:** If plural is non-empty after parse, use plural only. Else fall back to singular. If both plural and singular are set, plural wins (documented); operators who want both keys in one deployment put both in the plural lists.

**Why parallel CF lists over `accountId:token` CSV:** Tokens can contain characters that complicate delimiter escaping; parallel lists match existing var names and are easy to extend in Vercel. Reject mismatched lengths (empty pool) rather than silent mis-pairing.

**Alternatives considered:** Numbered suffixes (`GROQ_API_KEY_2`) — rejected as harder to discover and document. Single `CLOUDFLARE_CREDENTIALS=id:token,...` — rejected due to delimiter risk.

### 2. Module shape (`backend/app/llm/key_pool.py`)

- `Credential` / provider-specific typed entries (Groq: api_key string; CF: account_id + api_token).
- `KeyPool` with: parse from env, `acquire()` → next eligible credential (round-robin index under a module-level lock), `mark_cooldown(credential_id, seconds)` on 401/403/429.
- Default cooldown: ~60s (constant, overridable later if needed).
- Helpers: `get_groq_pool()`, `get_cloudflare_pool()` that rebuild from env when env changes in tests (or cache with clear for tests).
- Redacted `label` for logs (e.g. `gsk_…ngcN`).

**Selection:** Round-robin among non-cooled-down entries (predictable under tests). Random is acceptable alternative; round-robin is easier to assert.

### 3. Provider wiring

- `call_groq`: obtain key from pool; on 401/403/429 mark cooldown and retry with next key (bound retries to pool size). Model rotation (`call_groq_with_rotation`) remains; key retry wraps each model attempt or wraps the outer call once — prefer **key retry inside `call_groq`** so both direct and rotation paths benefit.
- `call_cloudflare`: same pattern with account_id+token pairs; introduce `CloudflareRateLimitError` (or reuse status_code on `CloudflareError`) so 429 is distinguishable.
- `suggestions.py` / `is_*_configured` checks: use “pool non-empty” instead of only singular env reads.

### 4. Second Cloudflare account id

Token verify for the second token succeeded (`active`), but `GET /accounts` returned zero results and `/user` was unauthorized — account id **cannot** be discovered from this token’s permissions. Leave `CLOUDFLARE_ACCOUNT_IDS` second slot as a documented placeholder until the user supplies the account id from the Cloudflare dashboard. Do not invent an id. Local `.env` may temporarily omit the second CF pair or use a placeholder the pool will skip if empty.

### 5. Process-local cooldown on Vercel

Cooldown is in-memory. Cold starts reset state (acceptable). Multiple concurrent instances may all hit the same key until each learns — still better than no rotation.

## Risks / Trade-offs

- **[Risk] Mismatched CF list lengths silently disable CF** → Mitigation: document clearly; unit test; prefer empty over wrong pairing.
- **[Risk] Secrets pasted in chat / logs** → Mitigation: redact helpers; never commit `.env`; remind operator to rotate if chat is retained.
- **[Risk] Cooldown not shared across serverless instances** → Mitigation: accept best-effort; revisit only if production still trips limits often.
- **[Trade-off] Plural wins over singular** → Operators migrating must put all keys in plural lists; singular remains for unchanged single-key deploys.

## Migration Plan

1. Ship code + `.env.example` + `AGENTS.md` with plural vars optional.
2. Locally merge keys into plural vars in gitignored `conf/.env`.
3. Production: optionally set `GROQ_API_KEYS` / CF parallel lists in Vercel; until then singular vars keep working.
4. Restart local docker backend (if used) so new env is picked up.
5. Rollback: unset plural vars; singular-only behavior restored.

## Open Questions

- Cloudflare account id for the second token must be supplied by the operator (dashboard Overview) before that pair can be activated locally/in Vercel.
