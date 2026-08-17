## Why

The shared correction-prompt editor tells the operator four things in Japanese, one of which is now the wrong answer to the question the operator actually asked. It says offline mode ignores the setting — but the whole point of an operator-owned prompt is that it governs how *this app* critiques, not how one transport does. It also never says where the pasted SOURCE / TARGET / EXEMPLAR text lands relative to the text being edited, so an operator writing a rule about the exemplar has no way to know whether the exemplar is even in the context at that point. And the editor is a `max-w-3xl` box for a document that is currently ~5,000 characters of dense Chinese rules, which is not a size anyone can read a rule set in.

## What Changes

- Offline mode (WebLLM) applies the stored shared prompt instead of always using its built-in one. **The built-in prompt remains the fallback** for the unset case, because it is deliberately condensed for a 7B model. The JSON output contract and the few-shot example stay code-owned and are still appended automatically, so this does not hand the operator a way to break parsing.
- The dialog's claim that offline mode ignores the setting is removed, because it becomes false.
- The dialog discloses the assembly order of the full prompt — the edited body, the exemplar rules, the JSON contract, the built-in example, then SOURCE / EXEMPLAR / TARGET — including that the two exemplar pieces appear only when the operator actually pasted an exemplar.
- The dialog's own copy becomes English: title, description, character counter, validation and request errors, attribution line, and the three footer buttons.
- The prompt editor gets a documented wide-dialog size rather than the default prose width, and a taller editing surface on viewports that have the room.
- **Not changed**: the provider failover order, and the rule that WebLLM is loaded and called only when offline mode is explicitly on. This change is about which prompt WebLLM uses once the operator has chosen it, not about when WebLLM runs.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `prompt-settings`: the stored prompt governs offline generation too, and the editor must disclose prompt assembly order rather than only its own field
- `ai-suggestion-generation`: offline WebLLM generation composes its prompt from the stored shared body when one exists, falling back to the built-in offline prompt otherwise

## Impact

- `frontend/src/components/ui/prompt-settings-dialog.tsx` — English copy, assembly disclosure, wide size
- `frontend/src/components/ui/dialog.tsx` — a named `size` for long-form editors
- `frontend/src/lib/webllm/prompt.ts`, `frontend/src/lib/webllm/prompts/system.ts` — split the built-in offline prompt into an editable body and a code-owned output contract so an override can replace the body without losing the contract
- `frontend/src/lib/promptComposition.ts` (new) — the single description of assembly order that the dialog renders and the tests assert against
- `frontend/src/app/page.tsx` — offline generation reads the stored prompt
- `docs/UI-DESIGN.md` (dialog width tokens), `docs/SYSTEM-DESIGN.md`, `AGENTS.md` — the offline path no longer keeps its own prompt
- No API, schema, or backend prompt-composition change
