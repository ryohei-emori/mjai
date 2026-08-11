## Context

`backend/app/llm/groq_provider.py` currently hardcodes `DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"`, overridable only via a single `GROQ_MODEL` env var (see `backend/tests/test_groq_provider.py` for current coverage). `backend/app/llm/suggestions.py` implements a two-tier failover: Groq (any error) → Cloudflare Workers AI → raise `SuggestionsError`. See `proposal.md` - Why for motivation.

**Live model catalog verification (done as part of this design, not deferred):** Since I do have web access in this environment, I fetched Groq's live documentation directly rather than guessing, per the proposal's ambiguity-handling instructions. Sources and timestamps (fetched 2026-08-11, from `console.groq.com/docs/models` and `console.groq.com/docs/deprecations`):

| Model ID | Status (as of 2026-08-11) | Category | Suitable for rotation? |
|---|---|---|---|
| `llama-3.3-70b-versatile` | **Production, but shutdown date 2026-08-16** (deprecation announced; replacement `openai/gpt-oss-120b` or `qwen/qwen3.6-27b`) | general chat | Yes, but time-limited — expect it to start erroring within days of this design being read; do not treat as a durable pool member |
| `llama-3.1-8b-instant` | **Production, but shutdown date 2026-08-16** (replacement `openai/gpt-oss-20b`) | general chat, small | Excluded — same imminent-shutdown issue, and was already the model the prior fix (commit `af381f9`) moved *away from* for quality reasons |
| `openai/gpt-oss-120b` | Production, no deprecation scheduled | general chat, reasoning | Yes |
| `openai/gpt-oss-20b` | Production, no deprecation scheduled | general chat, reasoning, smaller/faster | Yes |
| `qwen/qwen3.6-27b` | **Preview** (not deprecated, but Preview tier: "may be discontinued at short notice", per Groq's own preview-model policy) | general chat, multimodal | Yes, per explicit user request to include Qwen — but flagged as higher operational risk than the two `gpt-oss` models |
| `qwen/qwen3-32b` | **Deprecated, shut down 2026-07-17** (already gone) | — | No — this id already 404s; do not use despite being the more commonly-referenced Qwen id in older docs/blog posts |
| `openai/gpt-oss-safeguard-20b` | Preview, safety/policy classification tuned | moderation | No (per proposal's exclusion criteria) |
| `groq/compound`, `groq/compound-mini` | Production systems, agentic (web search / code exec) | agentic | No (per proposal's exclusion criteria; also only 250 RPD vs 1K+ for the chat models) |
| `meta-llama/llama-prompt-guard-2-22m/86m` | Preview, classifier | classifier | No (per proposal's exclusion criteria) |
| `allam-2-7b` | Production | general chat (Arabic-focused) | No — not evaluated for Japanese quality, out of scope for this proposal; excluded for now |

This directly changes the urgency calculus from the proposal: **`llama-3.3-70b-versatile` alone, as currently hardcoded, will start failing in days.** This design's allow-list must not rely on it surviving past 2026-08-16.

## Goals / Non-Goals

**Goals:**
- Define a concrete, durable (not about-to-be-deprecated) allow-list of Groq models for the rotation pool.
- Decide a selection strategy that works correctly given Vercel's per-invocation-stateless serverless execution model.
- Decide the exact retry-before-fallback behavior and bound it so worst-case latency stays acceptable for a synchronous suggestion-generation request.
- Keep `GROQ_MODEL` as an escape hatch that fully disables rotation.

**Non-Goals:**
- Building a persistent/distributed rotation-state store (e.g. Redis, DB-backed counter). Explicitly rejected — see Decisions.
- Automatically re-fetching Groq's live `/v1/models` endpoint at runtime to self-update the allow-list. The allow-list is a static, reviewed constant; catalog drift is handled by periodic manual review (a task item), not runtime discovery.
- Per-model prompt tuning. The current Japanese prompt (`backend/app/llm/prompts.py`) is assumed compatible across all rotation candidates (see Decisions below for why).
- Changing the Cloudflare or WebLLM tiers of the failover chain.

## Decisions

### 1. Allow-list contents

**Decision:** Rotation pool = `["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.6-27b"]`. Do **not** include `llama-3.3-70b-versatile` or `llama-3.1-8b-instant` in the durable allow-list, despite one of them being the current pre-change default — both have a confirmed shutdown date of 2026-08-16, so shipping them as rotation-pool members would just reintroduce the single-model-deprecation risk this change exists to fix, on a multi-day delay.

- `openai/gpt-oss-120b` and `openai/gpt-oss-20b`: both Production-tier, no scheduled deprecation, both explicitly listed by Groq as the recommended replacements for the two models being retired. Include both — 120B for quality, 20B for speed/cost, and having two stable anchors means rotation survives even if one of them is deprecated later.
- `qwen/qwen3.6-27b`: included per the user's explicit request to have Qwen in the pool. It is **Preview tier**, meaning Groq may pull it at short notice — this is a real operational risk, not a formality. Recommendation: keep it in the pool but treat `openai/gpt-oss-120b` and `openai/gpt-oss-20b` as the load-bearing members; if `qwen/qwen3.6-27b` starts erroring, the in-provider retry (Decision 3) already covers falling through to a `gpt-oss` model within the same request.
- **Alternative considered:** keep `llama-3.3-70b-versatile` in the pool until its 2026-08-16 shutdown, then remove it in a follow-up. Rejected — the shutdown date is within the expected implementation window for this change, so including it would require a same-week follow-up removal for no real benefit; simpler to ship the durable 3-model pool now.
- **Verification task:** confirm `qwen/qwen3.6-27b` (and the two `gpt-oss` ids) are still live via `GET https://api.groq.com/openai/v1/models` with a real `GROQ_API_KEY` before/during implementation — the table above is current as of this design's fetch (2026-08-11) but Groq's catalog changes on short notice by design (see Preview-tier policy).

### 2. Selection strategy given serverless statelessness

**Decision:** `random.choice(ALLOWED_GROQ_MODELS)` per request, no persistent counter.

Vercel serverless functions are stateless per-invocation (cold starts especially), so an in-memory round-robin counter (e.g. a module-level index incremented on each call) would almost never actually rotate in production — most invocations get a fresh process and the counter resets to its initial value, collapsing "rotation" back down to "always pick the first model." A literal round-robin therefore requires external state (e.g. a DB row, Redis `INCR`, or a KV store), which is disproportionate infrastructure for a single-user app whose goal is simply "don't hammer one model."

`random.choice` achieves the actual goal — spreading requests across models to avoid concentrating load/failures on one model id — without any external state, and is operationally equivalent to round-robin for load-distribution purposes at this app's request volume (single-user, well under any model's RPM/RPD ceiling even under worst-case uniform-random skew). This is the "simplest viable approach" called for in the proposal.

- **Alternative considered — in-memory module-level counter:** Works correctly only for long-lived processes (e.g. local dev, `uvicorn` with no cold starts); silently degrades to non-rotating in Vercel production, which is the primary deployment target per `AGENTS.md`. Rejected as misleading — it would look like round-robin in local testing and not behave that way in production.
- **Alternative considered — hash of request content or timestamp modulo pool size:** No real benefit over `random.choice` here (both are effectively uniform pseudo-random from the caller's perspective for a single-user app with irregular request timing) and adds complexity (must pick a stable hash input) for no gain. Rejected in favor of the simpler `random.choice`.
- **Alternative considered — external counter (DB row / KV):** Gives true round-robin sequencing. Rejected for this app: adds a network round-trip and a new failure mode (counter store unavailable) to the hot path of every suggestion request, for a load-distribution property (`random.choice`) that's already statistically equivalent at this app's traffic volume. Revisit only if per-model quotas start actually being hit in practice.

### 3. Retry-before-fallback bound

**Decision:** On a retriable Groq error (429/5xx/timeout) with rotation enabled, retry exactly once more against a different model drawn from the allow-list (i.e. **maximum 2 Groq attempts total** per request), then fall back to Cloudflare if that second attempt also fails retriably.

Rationale: Groq's own timeout is 10s (`GROQ_TIMEOUT`); allowing 2 attempts caps the Groq phase at ~20s worst case before falling to Cloudflare (15s timeout), keeping total worst-case request latency in a boundable, roughly-known range rather than open-ended (e.g. retrying across all 3 pool models before fallback could add up to ~30s of pure Groq-side latency on top of the eventual Cloudflare attempt). Two attempts also gives useful signal: if 2 of the (currently) 3 pool models are simultaneously failing, that's very likely a Groq-wide outage where a 3rd attempt is unlikely to help — better to fail over.

- **Alternative considered — retry all pool models before falling back:** Rejected for the latency reason above; also unnecessary complexity for a 3-model pool where testing 2 already covers "is this one model's problem or Groq's problem" reasonably well.
- **Alternative considered — no in-provider retry, fail over to Cloudflare on first Groq error (current behavior):** Rejected — this throws away the main benefit of rotation (resilience to a single model's transient issues) and always pays Cloudflare's typically-higher latency (~2-5s vs ~1-3s) on any transient single-model hiccup.
- The second model MUST differ from the first attempt (sampled from the remaining pool, or via `random.sample(pool, 2)` up front) — retrying the *same* randomly-selected model twice would not actually diversify away from whatever caused the first failure.
- `GROQ_MODEL` override bypasses this entirely (single pinned model, no in-provider retry) — this matches the existing pre-change failover behavior exactly when rotation is disabled, so there is no regression for anyone relying on `GROQ_MODEL` for pinning/debugging today.

### 4. `GROQ_MODEL` semantics

**Decision:** unchanged env var, but its meaning is now explicitly "disable rotation, pin to exactly this model" rather than "the only model that was ever going to be used anyway." No code changes needed to `get_groq_model()`'s existing precedence — only need a new `is_rotation_enabled()`-style check (`GROQ_MODEL` unset/empty → rotation on) gating the new selection/retry logic, leaving the existing single-model code path fully intact for the override case.

### 5. Prompt compatibility across rotation candidates

The current Japanese prompt (`backend/app/llm/prompts.py`, ported off the Chinese WebLLM prompt as part of the prior fix in commit `af381f9`) is a plain instruction + one-shot example targeting a generic "follow instructions, emit strict JSON" capability — it does not depend on any model-specific formatting (e.g. no model-specific chat template quirks, no reliance on a particular context window size well beyond what any candidate model supports at 131K tokens). All three rotation candidates (`openai/gpt-oss-120b`, `openai/gpt-oss-20b`, `qwen/qwen3.6-27b`) are general-purpose instruction-tuned chat models with equal or greater parameter count / capability than `llama-3.3-70b-versatile`, which the prompt is already confirmed (per this conversation's live test) to work correctly with. No prompt changes are planned. Tasks include a manual verification step per candidate model as a safety net, not because prompt incompatibility is expected.

**Implementation-time finding (task 6.1 live smoke test):** this assumption held for `openai/gpt-oss-120b` and `openai/gpt-oss-20b` (clean JSON at default settings) but **not** unmodified for `qwen/qwen3.6-27b` — it is a reasoning model that, at Groq's default `reasoning_effort` ("default"), emits a `<think>...</think>` block inline in the response content before the final answer. With this prompt's `max_tokens: 1024` budget, the thinking block was observed to consume the entire budget, truncating the response before any JSON appeared; `parse_model_output()` then fell back to extracting the system prompt's own placeholder text (`"該当箇所の抜粋"` etc.) as if it were a real suggestion — a silent correctness failure, not an exception, so it would not have triggered the in-provider retry or Cloudflare fallback added by this change. Fix (implemented, not a scope change): send `reasoning_effort: "none"` in the Groq request payload specifically for `qwen/qwen3.6-27b` (`QWEN_REASONING_MODELS` in `groq_provider.py`), which Groq's `/docs/reasoning` confirms is supported for this model family to fully disable the inline thinking block. Re-verified via live smoke test after the fix: clean, correctly-parsed JSON output. `openai/gpt-oss-*` models do not accept `"none"` for `reasoning_effort` (only `low`/`medium`/`high`) and don't need it, since they don't inline a thinking block in content at default settings.

### 6. Where the logic lives

Selection, retry-across-models, and the allow-list constant live entirely inside `backend/app/llm/groq_provider.py` (a new internal function, e.g. `call_groq_with_rotation()`, wrapping the existing single-attempt `call_groq()`). `backend/app/llm/suggestions.py`'s failover loop calls this wrapper exactly where it currently calls `call_groq()` directly, and its Groq-vs-Cloudflare fallback logic is otherwise unchanged — it does not need to know how many Groq models were tried internally. This keeps the failover chain's public shape (Groq tier → Cloudflare tier) exactly as `suggestions.py` and its existing tests already model it.

## Risks / Trade-offs

- **[Risk]** `qwen/qwen3.6-27b` is Preview-tier and could be pulled with little notice, same as `qwen/qwen3-32b` was → **Mitigation**: in-provider retry (Decision 3) means a single request surviving a `qwen3.6-27b` outage just needs one of the two `gpt-oss` models to be healthy; no user-visible failure from losing one pool member. Revisit the allow-list if Groq deprecates it.
- **[Risk]** `random.choice` does not guarantee strict per-request fairness (a run of bad luck could pick the same model several times in a row) → **Mitigation**: acceptable for a single-user app well under any candidate's rate limits; not worth the added complexity of true round-robin under Vercel's statelessness (see Decision 2).
- **[Risk]** The allow-list is a static constant that can silently drift out of date if Groq deprecates one of the 3 remaining pool models later → **Mitigation**: `tasks.md` includes updating `AGENTS.md`'s model table, which is the existing convention for tracking this; no automated catalog-refresh mechanism is in scope (see Non-Goals).
- **[Risk]** Bounding retries to 2 Groq attempts means a genuine multi-model Groq outage still takes ~20s before falling to Cloudflare, worse than today's fail-fast-to-Cloudflare-on-first-error behavior → **Mitigation**: accepted trade-off per Decision 3; this only triggers when the *first* selected model is already failing, which is the less common path, and the alternative (no in-provider retry) gives up rotation's main resilience benefit entirely.

## Migration Plan

No data migration. This is a pure code + config change:
1. Ship the allow-list + selection + retry logic behind the existing `GROQ_MODEL` precedence (unset → new rotation behavior; set → old pinned behavior, zero behavior change for anyone with it set).
2. No deployment-order dependency — this is a single backend deploy, no frontend or schema changes.
3. Rollback: revert the `groq_provider.py`/`suggestions.py` changes, or set `GROQ_MODEL=openai/gpt-oss-120b` (or another known-good id) in Vercel env vars to pin to a single model without a code rollback, if rotation itself is suspected of causing an issue.

## Open Questions

- Should `allam-2-7b` be evaluated for Japanese-language quality and potentially added to the pool later? Out of scope for this change (proposal explicitly excludes it pending evaluation); can be revisited independently without touching this change's specs or approach.
- If Groq later deprecates `qwen/qwen3.6-27b` (plausible, given it's Preview-tier and its predecessor `qwen/qwen3-32b` was deprecated after less than a year), should its replacement be added automatically or does the allow-list require a manual proposal-level update? Recommendation (not blocking): treat any allow-list change as a small follow-up change, not a runtime auto-discovery feature — consistent with this design's Non-Goals.
