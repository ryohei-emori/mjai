# Design

## Context

`editable-prompt-model-log-and-critique-fix` shipped the shared prompt as a *cloud-path* setting: `backend/app/llm/prompts.py` splits into `SYSTEM_PROMPT_BODY` (replaceable) and `OUTPUT_CONTRACT` (code-owned, always appended last), and `/suggestions` reads `app_settings.correction_system_prompt` per request. The offline path (`frontend/src/lib/webllm/`) kept a single monolithic `SYSTEM_PROMPT` with the JSON contract embedded in the middle of it, and had no seam for an override. The dialog disclosed that split as a limitation. This change closes it.

## Goals / Non-Goals

**Goals**
- One prompt governs both paths; the offline built-in prompt becomes the unset-case fallback.
- The editor tells the truth about assembly order, verifiably.
- The editor is sized from a named, documented size.

**Non-Goals**
- Failover order (Gemini → Groq → Cloudflare) is untouched.
- WebLLM's *launch* condition is untouched: offline mode only, no automatic fallback.
- No API, DB, or backend prompt-composition change. The backend already accepts an override.

## Decisions

### Decision 1: Split the offline prompt around the contract, without reordering the default

The backend could put `OUTPUT_CONTRACT` at the end because its body was authored that way. The offline prompt cannot: its JSON-only instruction sits on line 2 and the `格式：` schema on line 4, with rules both above and below. Appending the contract at the end would give the offline default a different byte sequence than the prompt that was actually tuned and measured against Mistral 7B — a silent behavioural change to the path this change is *not* trying to alter.

So `system.ts` splits into three parts and the default reassembles them in place:

```
SYSTEM_PROMPT = SYSTEM_PROMPT_HEAD + OUTPUT_CONTRACT + "\n" + SYSTEM_PROMPT_TAIL
```

`SYSTEM_PROMPT` therefore stays byte-identical, and the override path composes the same way the backend does:

```
override + "\n" + OUTPUT_CONTRACT
```

The override drops `SYSTEM_PROMPT_TAIL` along with the rest of the built-in body — which is correct and matches the backend, where an override replaces the whole rules body. The pieces an override must never lose (JSON-only, the schema, and the field-language rule that keeps `original` / `sourceExcerpt` in Japanese) are all inside `OUTPUT_CONTRACT`.

**Rejected**: keeping `SYSTEM_PROMPT` as a fourth literal alongside the three parts. Two sources for the same text drift.

### Decision 2: Compose the offline system prompt through a function that mirrors the backend

`buildSystemPrompt(exemplar, override)` in `webllm/prompt.ts` mirrors `build_system_prompt` in `prompts.py`:

| override | exemplar | result |
|---|---|---|
| absent | absent | `SYSTEM_PROMPT` |
| absent | present | `SYSTEM_PROMPT` + exemplar rules |
| present | absent | override + contract |
| present | present | override + exemplar rules + contract |

The two `absent`-override rows are byte-identical to today's `buildPrompt`, which is what the regression test pins.

### Decision 3: Only a *customized* prompt overrides the offline built-in

`GET /settings/prompt` returns the effective prompt, which equals the backend default when nothing is stored. Passing that through unconditionally would replace the 7B-tuned offline prompt with ~5,000 characters of cloud-oriented Chinese rules for every offline user who never touched settings — a large, unrequested quality change on the path with the smallest instruction budget. So `page.tsx` sends the override only when `isCustomized` is true, and swallows fetch failures to `undefined`. Offline mode is exactly the situation where that fetch is most likely to fail, and a settings outage must not become a generation outage.

### Decision 4: One composition description, asserted against both builders

The requirement "the disclosure must not drift from what is sent" needs a mechanism, not a promise. `frontend/src/lib/promptComposition.ts` exports `PROMPT_COMPOSITION_STEPS` — an ordered list of `{ id, label, detail, conditional }`. The dialog renders it; it holds no copy of its own. Tests then close the loop from both ends:

- A frontend test drives the real `buildPrompt` with distinctive marker strings and asserts the marker offsets increase in the order the steps declare, and that the `conditional` steps vanish when the exemplar is blank.
- A backend test asserts the same order across `build_messages`' three messages.

If someone reorders a builder, a test fails naming the step. This is the guarantee; the prose in the dialog is downstream of it.

Order, read off the builders rather than asserted from memory:

| # | Step | Cloud (`build_messages`) | Offline (`buildPrompt`) |
|---|---|---|---|
| 1 | Your prompt | system msg, first | prompt head |
| 2 | Exemplar rules (conditional) | system msg, after body | after body |
| 3 | JSON output contract | system msg, last | inside the built-in default; appended last for an override |
| 4 | Built-in example | user msg #1 | after the system section |
| 5 | SOURCE TEXT | user msg #2 | `## 問題` section |
| 6 | EXEMPLAR TEXT (conditional) | user msg #2, after SOURCE | after SOURCE |
| 7 | TARGET TEXT | user msg #2, after EXEMPLAR | after EXEMPLAR |

Step 3's offline position is the one place the two paths differ, and it differs only for the *default* prompt, where the contract is interleaved for 7B reasons (Decision 1). For an edited prompt — the only case the editor's disclosure is about — both paths append it last. The step's `detail` says "always appended by the system" rather than claiming a position, so the statement is true on both paths.

### Decision 5: Dialog width becomes a named size, not a call-site value

`docs/UI-DESIGN.md` gets two dialog widths — `prose` (`max-w-3xl`, the existing default) and `wide` (`max-w-5xl`, long-form editors) — and `DialogContent` grows a `size` prop that selects between them. The prompt editor asks for `wide`. A one-off `className="max-w-5xl"` at the call site would satisfy the visible complaint and leave the next editor to guess.

The textarea floor goes from `min-h-[8rem]` to `min-h-[12rem] sm:min-h-[24rem]`. The floor is what the mobile-keyboard fix in `responsive-mobile-correction-ui` turned on: `flex-1` lets the box grow, and the floor is what it may not shrink below. Raising the floor unconditionally would re-break the footer on a phone, so the tall floor is behind `sm:`.

### Decision 6: English copy, and what the description keeps

The description keeps three facts and drops nothing else: the prompt's purpose, that it is shared and persistent, and that the JSON format is automatic. The requested phrasing "saved in all users" is not English, so it becomes "Shared across all users and sessions". The removed offline note is not replaced by an inverted one — the composition disclosure now covers "what this prompt governs", and a note saying "this also applies offline" would be re-describing the default.

## Risks / Trade-offs

- **A cloud-oriented custom prompt on a 7B model.** An operator's prompt is written against Gemini and may exceed what Mistral 7B follows, so offline critique quality can drop after a customization. This is the behaviour that was asked for, and it is opt-in per customization; the built-in prompt remains one reset away. Mitigation is documentation, not code.
- **One extra request per offline job.** `getPrompt()` runs per job rather than once. Offline concurrency is capped at one job, so this is one small request per generation, and its failure path is already a no-op fallback.
- **An override loses `SYSTEM_PROMPT_TAIL`.** Consistent with the backend, and stated in the docs; the parts that protect parsing are in the contract.
