## Context

See proposal.md — Why. Today `_generate_suggestions_once` in `backend/app/llm/suggestions.py` tries Groq → Cloudflare → Gemini with same-pass content salvage and an outer Chinese/JSON retry loop. Key pools, timeouts, and 503 `*_pool_size` diagnostics stay as built by `add-gemini-api-key-pool` / `fix-quota-pool-retry`.

## Goals / Non-Goals

**Goals:**
- Reorder the single-pass chain and salvage to Gemini → Groq → Cloudflare with minimal code churn.
- Keep outer retry nudges, pool diagnostics, and “any of three configured” checks coherent.
- Align AGENTS.md, SYSTEM-DESIGN.md, and `.env.example` comments with the new order.

**Non-Goals:**
- Changing API keys, env var names, model allow-lists, or timeouts.
- Automatic WebLLM fallback.
- Removing Groq or Cloudflare from the chain.

## Decisions

### Decision 1: Reorder inside `_generate_suggestions_once` only

**Choice:** Swap the try-blocks so Gemini runs first, then Groq, then Cloudflare; update log messages and module docstrings accordingly.

**Rationale:** All salvage/`best_soft`/`SuggestionsError` plumbing already works for any order; only call sequence and “falling back to X” strings need to change.

**Alternatives considered:**
- Parallel fan-out — rejected (cost/quota, harder salvage semantics).
- New abstraction layer — rejected (overkill for a reorder).

### Decision 2: Accept higher happy-path latency

**Choice:** Document that Gemini primary may increase p50/p95 vs Groq-first (Gemini timeout ~45s vs Groq ~25s; typical Gemini latency often higher than Groq’s ~1–3s).

**Rationale:** Explicit operator preference for quality-first; failover still covers Gemini quota/errors.

### Decision 3: Tests assert new order

**Choice:** Update `test_llm_suggestions.py` so success/salvage/failover cases expect Gemini-first (mock Gemini unset or failing when testing Groq/CF paths; add Gemini-primary success).

## Risks / Trade-offs

- **[Risk] Slower happy path when Gemini is configured** → Accepted; document in AGENTS/SYSTEM-DESIGN; Groq/CF remain failover.
- **[Risk] Gemini free-tier quota hits more often as primary** → Pool + Groq/CF failover unchanged; ops still check per-project quotas.
- **[Risk] Stale docs/tests claiming Groq-first** → Tasks cover AGENTS, SYSTEM-DESIGN, `.env.example`, and pytest.

## Migration Plan

1. Ship code + docs; no env migration required.
2. Rollback: restore prior call order in `suggestions.py` (and matching docs/tests).

## Open Questions

None.
