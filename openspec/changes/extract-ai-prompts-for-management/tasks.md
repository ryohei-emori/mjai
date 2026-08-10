## 1. Setup

- [x] 1.1 Create `frontend/src/lib/webllm/prompts/` directory

## 2. Extract Prompts

- [x] 2.1 Create `prompts/system.ts` with SYSTEM_PROMPT constant
- [x] 2.2 Create `prompts/fewShot.ts` with FEW_SHOT_EXAMPLES constant
- [x] 2.3 Create `prompts/templates.ts` with section templates (SECTION_ORIGINAL, SECTION_TARGET, SECTION_INSTRUCTION, SECTION_ANSWER)
- [x] 2.4 Create `prompts/index.ts` to re-export all prompts

## 3. Refactor prompt.ts

- [x] 3.1 Update `prompt.ts` to import from `./prompts`
- [x] 3.2 Remove hardcoded SYSTEM_PROMPT and FEW_SHOT_EXAMPLES from `prompt.ts`
- [x] 3.3 Update `buildPrompt` function to use imported templates for section headers

## 4. Tests

- [x] 4.1 Verify existing `prompt.test.ts` tests pass without changes
- [x] 4.2 Add test to verify prompts are exported from prompts/index.ts

## 5. Documentation

- [x] 5.1 Update AGENTS.md with prompt management section (file locations, how to edit prompts, no backend deploy needed)
