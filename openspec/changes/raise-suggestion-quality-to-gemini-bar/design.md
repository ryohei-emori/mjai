## Context

See proposal.md — Why. `harden-semantic-suggestion-reasons` is complete (Chinese, accessible why, anti-false-缺少, absolute 「」 forbid + retry). This change raises the **quality bar** toward Gemini-style critique structure on Groq / Cloudflare / WebLLM only — no Gemini provider. Schema stays `original` + `reason` + optional `sourceExcerpt`. Leave `add-optional-exemplar-translation-input` untouched.

## Goals / Non-Goals

**Goals:**

- Prompt levers for Gemini-like output: constructive `overallComment`; `現状 → 推奨` + plain Chinese why in each `reason`; CN→JP literary/academic domain.
- Quote reconciliation: 「」 allowed only for Japanese TARGET citations; Chinese meta uses `""` / `“”`.
- Narrow corner-quote retry so legitimate 「叙事詩」 cites do not burn retry budget.
- Short Gemini-shaped few-shot + quality-bar fixtures (no live LLM in CI).

**Non-Goals:**

- Reintroducing Gemini / `GEMINI_*` as a provider.
- Expanding API/DB with a separate `suggested` field.
- Full NLP validation that every reason matches Gemini quality (prompt + fixtures only).
- Editing `add-optional-exemplar-translation-input`.

## Decisions

### 1. New focused change (not extend harden-*)

**Choice:** `raise-suggestion-quality-to-gemini-bar` as a new change.

**Rationale:** Prior change is 10/10 done and already dense (accessibility, quotes, SOURCE fidelity, coverage). Quality-bar structure is a distinct product goal; cleaner review/archive boundary.

### 2. Quality levers mapped from Gemini samples (prompt-only)

| Gemini pattern | Lever |
|---|---|
| Opening praise + skeleton assessment | `overallComment`: strengths then gaps |
| `誤り → 推奨（読み）` + Chinese why | Put `現状 → 推奨` inside `reason`; keep schema |
| Academic 专名 / 规范译词, register, calque, modality, voice… | Domain framing + few-shot exemplars |
| Dense multi-paragraph coverage | Keep harden coverage guidance; relax “1–2 sentences only” where it blocks density (still warn against truncation spam) |
| Non-translator-readable why | Reinforce existing accessibility MUST |

**Alternative considered:** Add `suggested` API field — rejected (UI/DB churn; Gemini content fits in `reason`).

### 3. Quote-mark policy (reconcile with harden)

**Choice:**

- Chinese meta-prose / Chinese cited words → `""` or `“”`.
- Japanese TARGET word/phrase citations (including recommended forms and optional readings) → 「」 **allowed and preferred** in few-shot for JP forms.
- Absolute “never 「」” from harden is **superseded** for JP cites only.

**Rationale:** Gemini wraps JP in 「」; Chinese readers still need Chinese quotes for Chinese labels. Mixing both is intentional.

### 4. Narrow `has_japanese_corner_quotes_in_critique`

**Choice:** Treat as **misuse detector**, not any-「」 detector:

1. Find complete `「…」` spans in `reason` / `overallComment`.
2. A span is an **allowed JP cite** if its inner text contains Japanese kana/halfwidth kana, **or** is a short kanji-only/shared-CJK citation (≤ ~16 chars) **without** Simplified-Chinese prose markers.
3. Return True (retry) if: unpaired 「/」, **or** any complete span looks like **Chinese prose** (simplified-only chars and/or Chinese critique labels such as 时态/语法/助词/问题/错误/缺少/不自然…).
4. Return False when every corner span is an allowed JP cite (e.g. 「叙事詩」「行きました」).

**Alternative considered:** Keep absolute forbid — rejected (fights Gemini-quality few-shot and burns retries). Strip-only without retry — rejected (Chinese-prose misuse would slip through).

**Keep:** `_strip_quoted_japanese_spans` still strips 「」 / `""` / `“”` for Chinese-language detection.

### 5. Few-shot + fixtures

**Choice:** Replace/expand backend + WebLLM few-shot with 1–2 short CN→JP literary examples showing:

- `overallComment` strengths → gaps
- reason like `史詩 → 叙事詩（じょじし）：…“史诗”…「叙事詩」。`
- `“”` for Chinese, 「」 for Japanese

Add `backend/tests/fixtures/gemini_quality_bar_cases.py` (reuse epic SOURCE/TARGET pointers or short excerpts) documenting desired shapes; optional cross-links from `semantic_reason_cases.py`. CI asserts prompts + heuristic only.

### 6. Provider / reinforce line

**Choice:** Update `suggestions.py` language reinforce if it still says absolute 禁止「」; align with JP-cite-allowed policy. No provider stack changes.

## Risks / Trade-offs

- **[Risk] Models still put Chinese inside 「」** → Mitigation: few-shot contrast; narrowed misuse retry.
- **[Risk] Kanji-only Chinese labels slip past short-span allowlist** → Mitigation: Simplified + critique-label marker list in heuristic; tests for 「时态」.
- **[Risk] Longer reasons increase truncation** → Mitigation: keep JSON mode / max_tokens; prompt “concise but complete”; no essay-length reasons.
- **[Risk] Prompt bloat on WebLLM** → Mitigation: ultra-short Chinese rule lines; one compact few-shot.

## Migration Plan

- Deploy with normal release (prompts + parser heuristic + tests). No DB migration.
- Rollback = revert commit. Prior absolute-forbid 「」 behavior returns if rolled back.

## Open Questions

- None material; optional later: archive-time merge of quote policy into main `ai-suggestion-generation` spec if desired.
