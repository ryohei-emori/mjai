-- Record which LLM produced a correction round's suggestions.
-- Apply to shared Supabase (SQL editor or CLI) before/with the deploy that writes these columns.
--
-- Kept separate from the existing `provider` column, which records the
-- transport (api | webllm) and is read that way by the UI badge. These two
-- columns record the concrete inference provider and the exact model id, so a
-- critique can be attributed to a model even though Gemini and Groq rotate
-- models per request. Rows written before this migration read back as NULL.

ALTER TABLE correction_histories
  ADD COLUMN IF NOT EXISTS llm_provider TEXT;

ALTER TABLE correction_histories
  ADD COLUMN IF NOT EXISTS llm_model TEXT;

COMMENT ON COLUMN correction_histories.llm_provider IS 'gemini | groq | cloudflare | webllm (inference provider, not transport)';
COMMENT ON COLUMN correction_histories.llm_model IS 'Exact model id that produced the suggestions, e.g. gemini-3.7-flash';
