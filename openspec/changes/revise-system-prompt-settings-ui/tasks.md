# Tasks

## 1. Offline prompt gains an override seam

- [x] 1.1 Split `frontend/src/lib/webllm/prompts/system.ts` into `SYSTEM_PROMPT_HEAD`, `OUTPUT_CONTRACT`, `SYSTEM_PROMPT_TAIL`, and reassemble `SYSTEM_PROMPT` from them so the default stays byte-identical
- [x] 1.2 Export the new parts from `frontend/src/lib/webllm/prompts/index.ts`
- [x] 1.3 Add `buildSystemPrompt(exemplar, override)` to `frontend/src/lib/webllm/prompt.ts` mirroring the backend's composition, add `systemPromptOverride` to `PromptInput`, and route `buildPrompt` through it

## 2. Offline generation reads the stored prompt

- [x] 2.1 In `frontend/src/app/page.tsx`, fetch the stored prompt for offline jobs and pass it as the override only when it is customized, falling back to the built-in prompt on any failure

## 3. Composition disclosure

- [x] 3.1 Add `frontend/src/lib/promptComposition.ts` with the ordered step list, marking the conditional exemplar steps
- [x] 3.2 Render the steps in the prompt editor as a collapsible section

## 4. Editor copy and size

- [x] 4.1 Translate the prompt editor's copy to English, remove the offline-mode note, and update the caller's save/reset toasts
- [x] 4.2 Add a `size` prop to `frontend/src/components/ui/dialog.tsx` selecting the prose or wide width, and raise the editor's textarea floor behind `sm:`

## 5. Tests

- [x] 5.1 Assert the offline prompt is byte-identical with no override, empty override and whitespace override
- [x] 5.2 Assert an override replaces the rules body while the contract and example survive
- [x] 5.3 Assert the real builders place their sections in the order `PROMPT_COMPOSITION_STEPS` declares, on both the frontend and the backend
- [x] 5.4 Update the dialog tests to the English copy and cover the composition disclosure
- [x] 5.5 Run `npm run lint`, `npm test`, `npm run build`, and `python -m pytest -m "not integration"`

## 6. Documentation

- [x] 6.1 Record the dialog width sizes and the revised editor layout in `docs/UI-DESIGN.md`
- [x] 6.2 Correct the "offline keeps its own prompt" statements in `docs/SYSTEM-DESIGN.md` and `AGENTS.md`
