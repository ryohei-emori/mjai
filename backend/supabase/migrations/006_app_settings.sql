-- Shared, operator-editable application settings (key/value).
-- Apply to shared Supabase (SQL editor or CLI) before/with the deploy that reads these rows.
--
-- One global row per setting key, shared by every allow-listed user — not per
-- user and not per browser. The only key today is 'correction_system_prompt',
-- holding the editable rules body of the AI correction system prompt.
--
-- Absence of a row means "built-in default in effect" rather than a copy of the
-- default text, so a later improvement to the default in code still reaches
-- anyone who has not customized the prompt. Reset therefore deletes the row.

CREATE TABLE IF NOT EXISTS app_settings (
    setting_key TEXT PRIMARY KEY,
    setting_value TEXT NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_by TEXT
);

COMMENT ON TABLE app_settings IS 'Global key/value settings shared by all allow-listed users';
COMMENT ON COLUMN app_settings.setting_key IS 'correction_system_prompt = editable rules body of the AI correction system prompt';
COMMENT ON COLUMN app_settings.setting_value IS 'Setting text; row absence means the built-in code default is in effect';
COMMENT ON COLUMN app_settings.updated_by IS 'Email of the account that last saved this setting (from the Supabase JWT)';

ALTER TABLE app_settings ENABLE ROW LEVEL SECURITY;

-- Same permissive policy as the other tables (per-user scoping is deferred).
-- Guarded so re-running this migration does not fail on an existing policy.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'app_settings'
          AND policyname = 'Allow all operations for authenticated users'
    ) THEN
        CREATE POLICY "Allow all operations for authenticated users"
            ON app_settings FOR ALL USING (true);
    END IF;
END
$$;
