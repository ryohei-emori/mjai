## 1. Platform and provider timeouts

- [x] 1.1 Raise `vercel.json` `functions.api/index.py.maxDuration` to 60
- [x] 1.2 Lower `GEMINI_TIMEOUT` to ≤25s (target ~22s) in `gemini_provider.py`; adjust CF timeout downward for tertiary path
- [x] 1.3 Add suggestions wall-clock budget (< maxDuration) that raises `SuggestionsError` before platform 504

## 2. Empty Gemini / diagnostics

- [x] 2.1 Confirm empty Gemini pool skips without HTTP hang (test if missing)
- [x] 2.2 Keep `gemini_pool_size` on 503 / logs; no secret values

## 3. Docs and tests

- [x] 3.1 Brief `AGENTS.md` note: Gemini HTTP timeout vs Vercel `maxDuration` vs wall-clock 503
- [x] 3.2 Unit tests for timeout constant / wall-clock abort / empty Gemini skip
- [x] 3.3 Run focused pytest for gemini + suggestions

## 4. Ops and ship

- [x] 4.1 Verify Production/Preview `GEMINI_API_KEYS` present (set from `conf/.env` only if missing); never print values
- [x] 4.2 Commit + push timeout/ops code (exclude unrelated prompt/exemplar work); redeploy so env + code take effect
