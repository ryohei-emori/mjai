-- Shared LLM credential availability, so a refusal is learned once instead of once per request.
-- Apply to shared Supabase (SQL editor or CLI) before/with the deploy that reads these rows.
--
-- Each serverless invocation runs in a fresh process, so the in-memory cooldown in
-- backend/app/llm/key_pool.py is discarded between requests: a user whose Gemini quota is
-- exhausted paid one 429 per pooled key on every generation, against the quota that was
-- already exhausted. These rows carry that knowledge across invocations.
--
-- Rows are state, not history: one row per (provider, model, credential) which is overwritten
-- rather than appended, so cardinality is bounded by providers x models x keys (tens of rows)
-- and no cleanup job is needed. A row whose recover_at has passed is inert.
--
-- The table's absence is not an error: the application treats it as "nothing learned yet" and
-- falls back to per-process cooldowns, so this migration and the deploy are order-independent.

CREATE TABLE IF NOT EXISTS provider_health (
    -- 'gemini' | 'groq' | 'cloudflare'
    provider TEXT NOT NULL,
    -- Model id when the provider's limits are per model (Gemini/Groq rotate models and a 429
    -- on one must not withhold the key from its sibling); '' when they are credential-wide.
    model TEXT NOT NULL DEFAULT '',
    -- Hash of the credential, never the credential. A pool index would be shorter but is
    -- positional: reordering GEMINI_API_KEYS would silently re-point every row at another key.
    credential_fingerprint TEXT NOT NULL,
    recover_at TIMESTAMP WITH TIME ZONE NOT NULL,
    reason TEXT,
    observed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    PRIMARY KEY (provider, model, credential_fingerprint)
);

COMMENT ON TABLE provider_health IS 'When each LLM credential is expected to be usable again; shared across serverless invocations';
COMMENT ON COLUMN provider_health.model IS 'Model the limit applies to, or empty string when the limit is credential-wide';
COMMENT ON COLUMN provider_health.credential_fingerprint IS 'Hash prefix identifying the credential; never the credential itself';
COMMENT ON COLUMN provider_health.recover_at IS 'Provider retry hint when it gave one, else the default cooldown; clamped so a bad value cannot withhold a credential indefinitely';
COMMENT ON COLUMN provider_health.reason IS 'Operator-facing note (e.g. HTTP status) for why the credential was refused';

-- Every read filters on "still in effect", which is the only access pattern.
CREATE INDEX IF NOT EXISTS idx_provider_health_recover_at ON provider_health (recover_at);

ALTER TABLE provider_health ENABLE ROW LEVEL SECURITY;

-- Same permissive policy as the other tables (per-user scoping is deferred).
-- Guarded so re-running this migration does not fail on an existing policy.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'provider_health'
          AND policyname = 'Allow all operations for authenticated users'
    ) THEN
        CREATE POLICY "Allow all operations for authenticated users"
            ON provider_health FOR ALL USING (true);
    END IF;
END
$$;
