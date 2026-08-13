## Context

See proposal.md — Why. Today `suggestions.py` runs Groq → Cloudflare with key pools in `key_pool.py`, shared prompts/parser, and no automatic WebLLM fallback. AGENTS.md still says not to configure `GEMINI_*` (legacy of the retired engine=gemini path). Live probes against the operator’s free-tier Generative Language API (2026-08) show `gemini-3.7-flash`, `gemini-3.6-flash`, `gemini-3.5-flash`, and `gemini-flash-latest` succeed, while `gemini-2.5-flash` / `gemini-2.5-pro` return 404 for these keys.

## Goals / Non-Goals

**Goals**
- Add Gemini as a third cloud provider with plural key pooling matching Groq’s pattern.
- Keep the happy path latency-first: do not insert Gemini before Groq/CF.
- Prefer stable free-tier Flash model IDs; support `GEMINI_MODEL` pin.
- Update AGENTS.md + SYSTEM-DESIGN for the new external dependency.

**Non-Goals**
- Restoring the old `engine=gemini` request-body switch or mock `BACKEND_MODE` path.
- Frontend exposure of Gemini keys; automatic WebLLM on cloud failure.
- Paid-only Pro models as defaults; Interactions API migration.
- Raising Google free-tier RPM/RPD via pooling alone (pool spreads keys; quotas may still be project-scoped).

## Decisions

### Decision 1: Failover order — Groq → Cloudflare → Gemini

**Choice:** Append Gemini after Cloudflare.

**Rationale:** Extends the existing chain without changing Groq/CF behavior or happy-path latency. Gemini free-tier RPM is low and latency is typically higher than Groq; putting it last makes it a quality/resilience salvage when faster providers fail or return unusable Chinese/JSON content.

**Alternatives considered:**
- Groq → Gemini → CF: better quality earlier, but increases p95 when Groq fails and demotes the already-working CF path — rejected to avoid breaking operational expectations.
- Gemini primary: contradicts speed-first architecture — rejected.

### Decision 2: Models — `gemini-3.7-flash` + `gemini-3.6-flash` rotation; pin via `GEMINI_MODEL`

**Choice:** Default allow-list `ALLOWED_GEMINI_MODELS = ["gemini-3.7-flash", "gemini-3.6-flash"]` with random/sample-style selection and one in-provider retry on a different pool model (mirror Groq). If `GEMINI_MODEL` is set, pin that id with no rotation.

**Rationale (research + live probe, 2026-08):**
| Candidate | Result | Notes |
|---|---|---|
| `gemini-3.7-flash` | HTTP 200 | Newest stable Flash on docs (“most capable Flash”); best free-tier quality candidate for bilingual critique + JSON |
| `gemini-3.6-flash` | HTTP 200 | Stable prior Flash; good rotation partner for 429/transient diversity |
| `gemini-3.5-flash` | HTTP 200 | Older Flash; omit from default pool to prefer newer quality |
| `gemini-flash-latest` | HTTP 200 | Floating alias — avoid as default (hot-swap risk); still pin-able via `GEMINI_MODEL` |
| `gemini-2.5-flash` / `2.5-pro` | HTTP 404 on probed keys | Not available for this free-tier project — exclude from default pool |

Prefer stable IDs over `-latest` for production predictability (Google documents 2-week notice before latest retargets, but pinned stables still change less often).

### Decision 3: REST `generateContent` (v1beta), not Interactions API / SDK

**Choice:** `httpx` POST to `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent` with `x-goog-api-key`, map chat `messages` → Gemini `system_instruction` + `contents`, request `generationConfig.responseMimeType = application/json` when supported, `maxOutputTokens` ≥ 4096.

**Rationale:** Matches existing provider style (no new Python SDK dependency); `generateContent` remains fully supported. Interactions API is newer but unnecessary for single-shot JSON critique.

### Decision 4: Credential pool in `key_pool.py`

**Choice:** Add `GeminiCredential`, `load_gemini_credentials`, `acquire_gemini`, `is_gemini_configured` using the same cooldown/round-robin machinery as Groq. Cooldown scope MAY be model-scoped (like Groq) so a 429 on one Flash model does not block the sibling model on the same key.

**Rationale:** One pool module keeps env conventions and test helpers consistent.

### Decision 5: Integrate salvage + diagnostics in `suggestions.py`

**Choice:** After CF soft-fail or CF network failure, try Gemini; include `gemini_pool_size` on `SuggestionsError` and in 503 JSON; `are_providers_configured()` true if any of Groq/CF/Gemini configured.

**Rationale:** Spec requires tertiary salvage and pool-size diagnostics without secrets.

### Decision 6: Docs replace “never GEMINI_*”

**Choice:** Update AGENTS.md AI provider tables and SYSTEM-DESIGN failover diagram/text to document Gemini pool ops; `.env.example` placeholders only.

## Risks / Trade-offs

- **[Risk] Free-tier quota is often per Google Cloud project, not per API key** → Pooling two keys from the same project may not double RPD; still useful for 401/key-revocation failover and if keys span projects. Document this caveat in AGENTS.md.
- **[Risk] Thinking/token overhead on Flash models** → Prefer JSON mime type + bounded max tokens; if empty/`finishReason=MAX_TOKENS` with only thought parts, treat as empty and continue failover/retry.
- **[Risk] Model 404s after Google deprecations** → Static allow-list + `GEMINI_MODEL` pin; maintenance note like Groq’s list.
- **[Risk] Keys pasted in chat** → Configure only gitignored/Vercel sensitive env; warn operator to rotate after setup (ops, not code).

## Migration Plan

1. Ship code with Gemini optional (chain works without Gemini keys).
2. Set `GEMINI_API_KEYS` in `conf/.env` (local) and Vercel production (+ preview if AI keys already mirrored).
3. Redeploy Vercel so serverless picks up new env.
4. Rollback: unset Gemini env vars — chain reverts to Groq → CF behavior.

## Open Questions

None material — failover order and model IDs resolved above from research + live probe.
