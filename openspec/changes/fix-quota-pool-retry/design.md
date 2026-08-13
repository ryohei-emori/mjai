## Context

Follow-up to `fix-key-pool-quota-and-lazy-webllm` and `add-llm-api-key-pool`. Next-key retry on 429 already works inside `call_groq()`. Operators still interpret “Quota Exceeded” as “pool must be empty / buggy.”

## Root cause ranking

1. **Misconception (most common):** Pool spreads load; it does **not** raise per-account Groq/CF RPD. Both keys at daily limit → fail even with `pool_size=2`. Local/prod both load plural env (2 Groq + 2 CF pairs observed by name/count).
2. **Code bug — model-global cooldown:** `mark_cooldown(cred.id)` is credential-wide. After model A 429s all keys, `call_groq_with_rotation`’s model B call sees `acquire_groq() is None` immediately → false “all keys cooled” without HTTP retry on B. Hurts when limits are **per-model**.
3. **Visibility change:** WebLLM auto-fallback removed → quota failures surface in UI (correct).
4. **Vercel cold start:** In-memory cooldown not shared → may re-hit depleted keys (extra 429s), not “skip healthy keys.”
5. **Parse-retry burn:** Up to 4 content passes × Groq rotation × CF can accelerate true RPD exhaustion (ops awareness; out of scope to remove).

## Decisions

### 1. Model-scoped cooldown for Groq

Cooldown map key: `{credential_id}::{model}` when a scope is provided. `call_groq` passes `resolved_model` into `acquire_groq` / `mark_cooldown`. Cloudflare keeps unscoped credential cooldown.

### 2. Diagnostics on 503

`SuggestionsError` + `POST /suggestions` JSON include `groq_pool_size` and `cf_pool_size`. Log once per generate attempt. No secrets.

### 3. Non-goals

- Scraping Groq/CF dashboards
- Shared Redis cooldown across Vercel isolates
- Changing frontend auto-fallback policy again
- Editing `page.tsx` / persist-suggestions work

## Risks

- **[Trade-off]** Org-wide RPD still fails both models → one extra round of HTTP 429s before CF. Acceptable; corrects per-model false-negatives.
- **[Risk]** Longer cooldown keys grow map → lazy expiry already pops expired entries.
