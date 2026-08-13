## Context

See `proposal.md` for motivation. Today the correction workspace center pane has two MD3 text cards — SOURCE TEXT (原文) and TARGET TEXT (翻訳/編集) — plus generate/job-queue UX. Draft text for SOURCE/TARGET (and suggestions) is persisted per session under `DRAFT_STORAGE_PREFIX` in `frontend/src/app/page.tsx`. Cloud generation goes through authenticated `POST /api/suggestions` with `originalText` / `targetText`; prompts are built in `backend/app/llm/prompts.py` (`build_user_prompt` / `build_messages`) and mirrored for WebLLM under `frontend/src/lib/webllm/prompts/`.

This change adds a third optional text input and threads it into those prompt builders only when non-empty. It is intentionally a separate OpenSpec change from any Chinese-language enforcement work.

## Goals / Non-Goals

**Goals:**

- Ship an optional exemplar-translation input that matches existing SOURCE/TARGET visual language.
- Keep empty-field generation identical to today's behavior.
- When filled, improve suggestion quality by giving the model a known-good translation reference.
- Persist the field client-side like other draft inputs; no server DB schema work.

**Non-Goals:**

- Requiring the exemplar for generation or for saving corrections.
- Persisting exemplar text into `correction_histories` / `ai_proposals` (or any Postgres column) in this change.
- Highlighting spans inside the exemplar textarea (no `HighlightedTextarea` requirement for this field).
- Changing Chinese-language enforcement / retry rules for `reason` / `overallComment`.
- Redesigning the overall workspace layout beyond inserting one card.

## Decisions

### 1. API / state field name: `exemplarTranslation`

**Choice**: CamelCase `exemplarTranslation` on the wire and in frontend session state, parallel to `originalText` / `targetText`.

**Alternatives considered**:
- `modelAnswer` / `modelTranslation` — ambiguous vs. the LLM itself.
- `exemplarText` — shorter but less explicit that it is a translation of the source.
- Japanese-only key — inconsistent with the English-key API convention documented in AGENTS.md.

### 2. Card placement: SOURCE → EXEMPLAR → TARGET

**Choice**: Insert the new card between SOURCE TEXT and TARGET TEXT in the center pane.

**Rationale**: Pedagogical reading order is original → known-good translation → learner attempt. Generate still keys off TARGET TEXT at the bottom of that stack.

**Alternatives considered**:
- After TARGET TEXT — also reasonable; rejected because the exemplar is a peer of SOURCE (fixed per exercise), not of the per-attempt TARGET.
- Collapsible / accordion — unnecessary complexity for a core optional input.

### 3. Bilingual header: `EXEMPLAR TEXT (模範回答訳文)`

**Choice**: Follow UI-DESIGN bilingual English-primary pattern (`SOURCE TEXT (原文)`, `TARGET TEXT (翻訳/編集)`). Exact subtitle may be tweaked at implement time (e.g. `模範訳`) as long as 「模範回答訳文」 meaning is preserved.

**Assumption**: Copy button in the card header, matching SOURCE/TARGET, for convenience.

### 4. Prompt inclusion: optional labeled section; omit when empty

**Choice**: Extend `build_user_prompt(original_text, target_text, exemplar_translation: str | None = None)` (and WebLLM template equivalent) so that when `exemplar_translation` is non-empty after strip, the user prompt gains a third block, e.g.:

```text
原文：...
模範回答訳文：...
添削対象：...
```

When empty/None, the middle block is absent — byte-for-byte same shape as today's two-block prompt aside from unrelated prompt edits elsewhere.

**Resolved at implement time**: the exemplar rules live in a separate `EXEMPLAR_REFERENCE_RULES` block appended to SYSTEM_PROMPT *only when the exemplar is non-empty*, rather than being written into SYSTEM_PROMPT unconditionally as this decision originally assumed. Same reason the empty section is omitted: telling a model about a 模範回答訳文 it cannot see is noise, and for the 7B WebLLM path it also costs instruction budget that the existing rules need. The behavior contract ("include when provided, omit when empty") is unchanged and now holds for the system message too — `build_system_prompt(None) == SYSTEM_PROMPT` exactly.

**Alternatives considered**:
- Always send an empty section — rejected; empty headings can confuse small models.
- Stuff into `instructionPrompt` — rejected; that field is legacy/unused in current cloud prompts and would not reach WebLLM cleanly.
- Unconditional system-prompt note — rejected per the resolution above.

### 4b. Guard the exemplar against copy-degeneration (validated by live A/B)

**Choice**: When the exemplar is present, the appended rules must state (a) 添削対象 is still judged against 原文, (b) "differs from the exemplar" is not itself a defect, (c) the exemplar must never be mentioned or cited inside `reason` / `overallComment`, and (d) "the exemplar writes it this way" is never an acceptable justification.

**Evidence** (`backend/scripts/live_exemplar_compare.py`, `gemini-3.7-flash`, epic multi-paragraph fixture, 2 replicates for baseline/guarded):

| Condition | Suggestions | Exemplar mentioned in critique | Prompt tokens |
|---|---|---|---|
| baseline (no exemplar) | 13, 13 | none | 3089 |
| guarded (exemplar + rules) | 11, 12 | none | 3723 |
| naive (exemplar, no rules) | 9 | none | 3495 |

The guarded runs additionally surfaced modality faults the baseline missed or buried — 「想像してみる」 losing the source's invitation to the reader, and 「聞き取るわけではない」 turning an objective "not everyone could hear it clearly" into a subjective denial. Those belong to the meaning-shift / modality categories the existing prompt already calls highest priority; the exemplar makes 原文 intent explicit enough for the model to see them.

The naive condition is the load-bearing result: an unguarded exemplar did *not* produce "the exemplar says X" prose, it produced **less coverage** (9 vs 13). So the risk to guard against is not verbal copying but the model settling for the diffs it happens to notice against a reference. Recommended Japanese forms in guarded runs do sometimes match exemplar wording verbatim; that is accepted and useful, because the surrounding `reason` still has to carry its own linguistic justification.

**Not verified live**: the WebLLM Mistral-7B path. Its rules are a two-line condensation of the backend's five, and are withheld entirely when the field is empty, so the offline no-exemplar path is provably unchanged; behaviour of a 7B model *with* an exemplar remains a manual-QA item.

### 5. Persistence: same `PersistedDraft` / debounce path; clear on save; keep on generate

**Choice**: Add `exemplarTranslation` to session state and `PersistedDraft`; include it in the existing 500ms debounced localStorage write; merge/restore with SOURCE/TARGET on `loadSessions` / session switch; clear on confirmed `saveCorrections()` with other draft fields.

**Assumption (explicit)**: After "AI提案を生成" queues a job, TARGET TEXT continues to clear; SOURCE and exemplar translation do **not** clear — both are fixed per exercise relative to the source text.

**Alternatives considered**:
- Ephemeral-only (no localStorage) — worse UX; users already expect draft survival for SOURCE/TARGET.
- Server persistence — out of scope; no history/proposal column this iteration.

### 6. No DB / proposals persistence

**Choice**: Exemplar is client draft + optional inference context only. Not stored on `POST /histories` or `POST /proposals`.

**Rationale**: Matches the proposal's scope and avoids a migration for an optional UX aid. Can be revisited later if histories need to show which exemplar was used.

### 7. Frontend generate payload

**Choice**: `suggestionsAPI.generate` (and WebLLM job path) pass `exemplarTranslation` only when trimmed non-empty; may omit the key entirely when empty (preferred) or send `""` — backend treats both as "omit from prompt."

### 8. Docs touch

**Choice**: Update `docs/UI-DESIGN.md` layout sketch + bilingual label table for the third card. Update `docs/SYSTEM-DESIGN.md` request-contract note for `/api/suggestions` if that section lists body fields. No AGENTS.md AI-architecture rewrite beyond a one-line request-field mention if the Response/Request schema section is adjacent.

## Risks / Trade-offs

- **[Risk] Longer prompts / token use when exemplar is pasted** → Measured: +634 prompt tokens (~21%) for a three-paragraph exemplar, output tokens and latency unchanged (~10-13s), well inside the Gemini 22s timeout and the 55s wall-clock budget. Field stays optional; no change to max_tokens policy.
- **[Risk] Model over-copies the exemplar instead of critiquing TARGET** → Measured (Decision 4b): the observed failure mode is reduced coverage, not verbal copying. Mitigated by the `EXEMPLAR_REFERENCE_RULES` guard, which no run violated across the probe.
- **[Risk] Draft schema version skew** (old localStorage drafts without the key) → Mitigation: read with `parsed.exemplarTranslation || ''` default, same pattern as other draft fields.
- **[Trade-off] No server-side audit of which exemplar was used** → Accepted for this iteration; client-only is enough for the stated UX goal.
- **[Trade-off] Separate from Chinese-enforcement Spec** → Intentional; avoids coupling optional-input UX to language-policy work.

## Migration Plan

1. Deploy frontend + backend together (additive optional field; old frontends omit the key and stay compatible).
2. No DB migration; no feature flag.
3. Rollback: revert the deploy; leftover `exemplarTranslation` keys in localStorage drafts are ignored by older code that does not read them.

## Open Questions

None blocking. Implement-time label microcopy (`EXEMPLAR TEXT` vs `MODEL ANSWER`) can be chosen to best match the mockup/UI-DESIGN tone without changing the specs.
