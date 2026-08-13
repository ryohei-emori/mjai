## ADDED Requirements

### Requirement: Document Gemini in the cloud failover architecture
Whenever Gemini is added as an external LLM dependency in the suggestions chain, `AGENTS.md` and `docs/SYSTEM-DESIGN.md` SHALL describe the as-built failover order (Groq → Cloudflare → Gemini), Gemini env vars (`GEMINI_API_KEYS` / `GEMINI_API_KEY` / `GEMINI_MODEL`), key-pool behavior, and that Gemini secrets are backend-only (never `NEXT_PUBLIC_*`). Obsolete guidance that forbids configuring `GEMINI_*` SHALL be replaced with current ops documentation.

#### Scenario: Ops docs mention Gemini pool after the change lands
- **WHEN** a contributor reads `AGENTS.md` and `docs/SYSTEM-DESIGN.md` after this change is implemented
- **THEN** both documents describe Gemini as part of the cloud suggestions failover chain
- **AND** they document plural/singular Gemini env conventions with placeholders only
- **AND** they do not instruct operators to avoid configuring `GEMINI_*` entirely
