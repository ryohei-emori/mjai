## ADDED Requirements

### Requirement: Document Gemini-primary failover order
Whenever the cloud suggestions failover order changes, `AGENTS.md` and `docs/SYSTEM-DESIGN.md` SHALL describe the as-built order **Gemini → Groq → Cloudflare Workers AI**, including that Gemini is primary (not tertiary). Comments in `conf/.env.example` that document failover order SHALL match. Obsolete Groq-primary / Gemini-tertiary wording SHALL be replaced.

#### Scenario: Ops docs match Gemini-first chain after the change lands
- **WHEN** a contributor reads `AGENTS.md`, `docs/SYSTEM-DESIGN.md`, and `conf/.env.example` after this change is implemented
- **THEN** all three describe Gemini → Groq → Cloudflare as the cloud suggestions failover order
- **AND** they do not claim Groq is primary with Gemini tertiary
