## Context

`vercel.json` sets `functions.api/index.py.maxDuration` to **30s**. Gemini provider uses `GEMINI_TIMEOUT = 45s` (already over the platform limit for one hung call). Groq is 25s; Cloudflare is 45s. In-provider rotation can double Gemini/Groq attempts; outer parse/language retries multiply the whole chain. Result: Vercel returns opaque `504 FUNCTION_INVOCATION_TIMEOUT` instead of app-level 503 with pool diagnostics.

`GEMINI_API_KEYS` is present on Production and Preview (set recently). Keys alone do not fix 504 if timeouts exceed `maxDuration`.

## Goals / Non-Goals

**Goals**

- Happy-path Gemini completes well under platform limit.
- Worst-case failover fails with app 503 before platform 504.
- Empty Gemini credential pool skips Gemini immediately.
- Ops docs state the timeout/`maxDuration` relationship.

**Non-Goals**

- Prompt / critique-format changes (owned by parallel coverage work).
- Changing failover order (already Gemini → Groq → CF).
- Raising free-tier provider quotas.

## Decisions

1. **Raise `maxDuration` to 60s** — Hobby/Pro allow ≥60s; gives headroom for Gemini happy path (~2–8s typical) plus one Groq attempt if needed.
2. **Lower `GEMINI_TIMEOUT` to 22s** — Primary must not alone exceed old 30s budget; two rotated models ≈ 44s worst case still fits 60s with little room → rely on wall-clock budget to cut further work.
3. **Lower `CF_TIMEOUT` to 20s** — Tertiary path; if we reach CF we are already late.
4. **Keep Groq at 25s** — Secondary; typically fast; one rotation attempt pair is rare.
5. **`SUGGESTIONS_WALL_CLOCK_S = 55`** — Soft stop before 60s hard kill; raise `SuggestionsError` so `main.py` returns 503 with pool sizes.
6. **Empty Gemini pool** — Already short-circuits via `get_gemini_api_key()`; keep as-is; add/assert in tests.

## Risks / Trade-offs

- Long Gemini generations that need >22s may fail over to Groq earlier (acceptable; Groq is fast secondary).
- Aggressive outer `MAX_PARSE_RETRY_ATTEMPTS=4` may hit wall-clock mid-retry and return 503 — preferred over 504.
- Pro plans could raise `maxDuration` further later; 60s is the portable default.

## Migration / Ops

- No DB migration.
- After code deploy, verify logs show `gemini_pool_size=2` (or pool count) and no 504 on suggestion generate.
- Env vars are already on Vercel; redeploy picks them up if a prior deploy predated the env add.
