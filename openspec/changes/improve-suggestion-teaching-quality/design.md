## Context

See proposal.md — Why. `raise-suggestion-quality-to-gemini-bar` already encodes structure (strengths→gaps, `現状 → 推奨`, CN→JP domain, quote policy). This change adds a **teaching bar** on the same prompt/spec surface so critiques target competence, not cosmetics. Parallel work on `add-gemini-api-key-pool` owns provider/env — do not touch it.

## Goals / Non-Goals

**Goals:**

- Prompt + few-shot levers that reject the three user anti-patterns and encourage essential / contrastive / class-of-error teaching.
- Keep backend ↔ WebLLM prompt sync; fixtures + unit assertions only (no live LLM in CI).
- Reinforce existing Gemini-bar MUSTS without regressing them.

**Non-Goals:**

- Editing `gemini_provider`, `GEMINI_*` env, key-pool wiring, or colliding with `add-gemini-api-key-pool`.
- Runtime NLP classifiers that score “teaching quality” on model output.
- API/DB schema changes; exemplar-translation input; `frontend/out` rebuilds.
- Auto-starting WebLLM on cloud failure.

## Decisions

### 1. New change (not reopen gemini-bar)

**Choice:** `improve-suggestion-teaching-quality` as a focused follow-on.

**Rationale:** Prior change is complete and archive-ready; teaching vs cosmetic is a distinct product contract. Cleaner review vs. amending archived tasks.

**Alternative:** Extend gemini-bar delta — rejected (already 9/9 complete; mixes two intents).

### 2. Prompt-only levers (no new parser heuristic)

**Choice:** Encode anti-patterns and desired patterns in `SYSTEM_PROMPT` / user reinforce / few-shot; assert via prompt tests + fixtures. Do **not** add a new parser retry heuristic for “cosmetic reason” (too fuzzy; burns retries).

**Rationale:** Teaching quality is semantic; false positives would retry good critiques. Fixtures document bad vs good shapes for humans and prompt regression.

**Alternative:** Keyword banlist (e.g. reject reasons containing “可以省略”) — rejected (brittle; Chinese phrasing varies).

### 3. Few-shot surgery over length explosion

**Choice:** Keep one short CN→JP literary few-shot; **replace** the weakest / most cosmetic-looking exemplar if present, and add one compliant contrastive lexical reason (e.g. modality or verb-nuance) plus a brief anti-pattern note in the system prompt. WebLLM stays ultra-short: compress teaching rules into 2–4 Chinese lines.

**Rationale:** Token budget for WebLLM; cloud can afford slightly denser SYSTEM rules.

**Concrete anti-pattern cues (from user):**

| Anti-pattern | Prompt cue |
|---|---|
| Trivial surface edit | 禁止把“可省略的表面简化”当作主指摘；应挖意义/语法/语域等实质问题 |
| Source-token swap | 禁止仅因原文用了某词就改成对应词形而无教学说明（那不是添削） |
| Preference without contrast | 词汇升级须先对比现状词与推荐词各自语感/语义，再说明为何推荐 |

### 4. Fixtures layout

**Choice:** Add `backend/tests/fixtures/teaching_quality_cases.py` with:

- Documented **bad** reason strings (trivial omit, bare source-swap, preference-without-contrast) — for documentation / negative examples in tests (not parser inputs).
- Documented **good** reason strings (contrastive lexical; class-of-error why for spelling/grammar).
- Cross-link note in `gemini_quality_bar_cases.py` pointing to teaching fixtures.
- Manual verify tips reusing epic or short corpora (same as quality bar).

**Alternative:** Only extend `gemini_quality_bar_cases.py` — acceptable if file stays readable; prefer dedicated file to keep gemini-bar archive-shaped content stable.

### 5. Collision boundary with Gemini pool

**Choice:** Hard file allow-list for this change: `prompts.py`, WebLLM `system.ts`/`fewShot.ts`, fixtures, prompt/Jest tests, this change’s OpenSpec artifacts. Never edit `gemini_provider.py`, `key_pool.py` Gemini paths, or `GEMINI_*` in env examples unless already required by unrelated docs (prefer leave alone).

## Risks / Trade-offs

- **[Risk] Models still emit cosmetic top hits** → Mitigation: strong negative examples in SYSTEM + few-shot contrast; manual verify on epic corpus.
- **[Risk] Over-long prompts hurt WebLLM** → Mitigation: ultra-short Chinese bullets in `system.ts`; denser rules only on backend.
- **[Risk] Accidental merge conflict with Gemini pool** → Mitigation: file allow-list; no provider edits.
- **[Trade-off] No runtime enforcement of teaching quality** → Accepted; same as gemini-bar (prompt + fixtures).

## Migration Plan

- Deploy is prompt-only: next backend/frontend deploy picks up new prompts automatically.
- Rollback: revert prompt/fixture commits; no DB migration.
- No env var changes.

## Open Questions

- None deferrable; user anti-patterns and desired patterns are specified.
