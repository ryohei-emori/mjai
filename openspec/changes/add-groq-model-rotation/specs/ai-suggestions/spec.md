## MODIFIED Requirements

### Requirement: Groq as primary provider

The system SHALL use Groq's OpenAI-compatible API as the primary inference provider, selecting a model **per request** from an explicit, curated allow-list of general-purpose instruction-following chat models known to produce coherent structured JSON output for this task, rather than always using one fixed model id.

The allow-list SHALL exclude models that are unsuitable for this task by category, specifically:
- Moderation/classifier models (e.g. `meta-llama/llama-prompt-guard-2-22m`, `meta-llama/llama-prompt-guard-2-86m`, `allam-2-7b`) — these are not general chat/completion models and cannot perform the correction task.
- Agentic/tool-use meta-models (e.g. `groq/compound`, `groq/compound-mini`) — these wrap tool-calling behavior (web search, code execution) atypical for a plain text-correction prompt and carry a much lower daily request quota (250 RPD).
- Safety/moderation-tuned variants (e.g. `openai/gpt-oss-safeguard-20b`) — tuned for policy/content-safety classification, not general correction output.

WHEN the `GROQ_MODEL` environment variable is set to a non-empty value, the system SHALL disable rotation entirely and use exactly that model id for every request, unchanged from prior behavior (backward compatible for pinning/debugging).

WHEN `GROQ_MODEL` is unset or empty, the system SHALL select a model for each request from the allow-list.

#### Scenario: Groq success path with rotation enabled

- **WHEN** `GROQ_API_KEY` is configured, `GROQ_MODEL` is unset, and the Groq API is available
- **THEN** the system selects a model from the allow-list, sends the inference request to Groq using that model, and returns the parsed response

#### Scenario: GROQ_MODEL override pins to a single model

- **WHEN** `GROQ_MODEL` is set to a specific model id
- **THEN** the system uses that exact model id for every request and does not rotate across the allow-list, regardless of the allow-list's contents

#### Scenario: Groq API key missing

- **WHEN** the `GROQ_API_KEY` environment variable is not set
- **THEN** the system immediately falls back to Cloudflare Workers AI without attempting model selection

#### Scenario: Unsuitable models are never selected

- **WHEN** the system selects a model for a request under rotation
- **THEN** the selected model is never a moderation/classifier, agentic/tool-use, or safety-tuned model as listed above

### Requirement: Cloudflare Workers AI failover

The system SHALL automatically retry within Groq's model rotation pool before failing over to Cloudflare Workers AI, bounding the number of Groq attempts to keep total latency predictable.

WHEN a Groq request fails with a retriable error (HTTP 429, HTTP 5xx, or a client-side timeout) and rotation is enabled (`GROQ_MODEL` is unset), the system SHALL retry the request against exactly one additional, different model drawn from the allow-list before falling back to Cloudflare Workers AI. WHEN rotation is disabled (`GROQ_MODEL` is set), or the retry against the second model also fails with a retriable error, the system SHALL fail over to Cloudflare Workers AI.

#### Scenario: Groq rate limited on first model, second model succeeds

- **WHEN** the first selected Groq model returns HTTP 429
- **THEN** the system retries the same request against a second, different model from the allow-list
- **AND** if the second model succeeds, the system returns its parsed response without falling back to Cloudflare

#### Scenario: Groq rate limited on both attempted models

- **WHEN** the first selected Groq model returns HTTP 429 and the retried second model also returns a retriable error
- **THEN** the system falls back to Cloudflare Workers AI

#### Scenario: Groq server error triggers same-provider retry then fallback

- **WHEN** the first selected Groq model returns HTTP 5xx
- **THEN** the system retries against a second Groq model before falling back to Cloudflare Workers AI if that retry also fails

#### Scenario: Groq timeout triggers same-provider retry then fallback

- **WHEN** the first selected Groq model request exceeds the Groq timeout
- **THEN** the system cancels the request, retries against a second Groq model, and falls back to Cloudflare Workers AI only if that retry also fails or times out

#### Scenario: GROQ_MODEL override skips in-provider retry

- **WHEN** `GROQ_MODEL` is set (rotation disabled) and the pinned model returns a retriable error
- **THEN** the system does not retry against a different Groq model and falls back directly to Cloudflare Workers AI, matching prior single-model behavior

#### Scenario: Both providers fail

- **WHEN** all attempted Groq models (up to two, under rotation) and Cloudflare Workers AI all fail or are unavailable
- **THEN** the system returns HTTP 503 with an error message indicating service unavailable
