## Why

Cloud/WebLLM critiques still emit rigid spoken labels like `现状：` / `推荐：` (and JP `現状：` / `推奨：`) because prompts and schema examples teach that machine template as the reason shape. Separately, Gemini often returns only ~2 suggestions on multi-paragraph TARGET—few-shot length, over-tight “concise” cues, and a 4096 `maxOutputTokens` budget that truncates dense pedagogical JSON—undermining the existing systematic coverage bar.

## What Changes

- Retarget prompt guidance (backend + WebLLM sync): keep problem → recommended fix → accessible why (and contrastive nuance) as **content** requirements, but **forbid** forcing spoken prefix labels `现状：` / `推荐：` / `現状：` / `推奨：` as the reason template.
- Update few-shots / schema examples so they demonstrate natural Simplified Chinese prose (optional `旧形 → 「新形」` contrast is fine) without training those colon labels.
- Strengthen multi-paragraph coverage guidance so models do not stop after ~2 real issues when more genuine problems exist; keep quality-over-padding (no fabricated items).
- Raise Gemini `maxOutputTokens` (and log `finishReason` when truncated) so longer multi-suggestion JSON is not cut mid-array.
- Update prompt/fixture unit tests accordingly. Failover order Gemini → Groq → Cloudflare stays unchanged.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `ai-suggestions`: Natural Chinese critique prose without mandatory `现状：`/`推荐：` spoken labels; stronger multi-paragraph coverage density; Gemini generation headroom for non-truncated suggestion arrays.

## Impact

- `backend/app/llm/prompts.py`, `frontend/src/lib/webllm/prompts/system.ts`, `fewShot.ts`
- `backend/app/llm/gemini_provider.py` (generationConfig / finishReason)
- `backend/app/llm/suggestions.py` (retry nudge wording if it re-teaches label prefixes)
- Backend/frontend prompt tests + quality-bar / teaching fixtures comments
- No API/DB schema change; no failover-order change; no secrets in git
