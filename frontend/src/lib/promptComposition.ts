/**
 * The one description of how a complete correction prompt is assembled.
 *
 * The prompt settings dialog renders this list so an operator can see where the
 * text they paste into the workspace ends up relative to the prompt they are
 * editing — the question "where does EXEMPLAR TEXT go?" has no answer from the
 * editor alone. It holds no copy of its own precisely so the answer cannot
 * drift: the builders are asserted against this order, on the frontend in
 * `lib/webllm/__tests__/promptComposition.test.ts` and on the backend in
 * `backend/tests/test_prompt_composition_order.py`. Reorder a builder and a
 * test fails naming the step.
 *
 * Order read off `build_messages` (backend/app/llm/prompts.py) and `buildPrompt`
 * (lib/webllm/prompt.ts), which agree:
 *
 *   cloud   system: body → exemplar rules? → contract
 *           user:   few-shot example
 *           user:   SOURCE → EXEMPLAR? → TARGET
 *   offline single message, same sequence
 *
 * `conditional` marks the two pieces that are withheld entirely when the
 * exemplar field is blank — never sent as an empty placeholder, so a prompt
 * written without an exemplar is byte-identical to one from before the field
 * existed.
 */
export type PromptCompositionStep = {
  id: string
  label: string
  detail: string
  /** Present only when the operator pasted an EXEMPLAR TEXT. */
  conditional?: boolean
}

export const PROMPT_COMPOSITION_STEPS: readonly PromptCompositionStep[] = [
  {
    id: "body",
    label: "Your prompt",
    detail: "The text you edit below — the critique rules.",
  },
  {
    id: "exemplar-rules",
    label: "Exemplar reference rules",
    detail:
      "Tells the model to treat EXEMPLAR TEXT as calibration only, never as the reason for a correction.",
    conditional: true,
  },
  {
    id: "contract",
    label: "JSON output format",
    detail: "Always appended by the system. You do not need to write it.",
  },
  {
    id: "few-shot",
    label: "Built-in worked example",
    detail: "A fixed example of a good critique, supplied by the system.",
  },
  {
    id: "source",
    label: "SOURCE TEXT",
    detail: "The source passage from the workspace.",
  },
  {
    id: "exemplar",
    label: "EXEMPLAR TEXT",
    detail:
      "Inserted between SOURCE TEXT and TARGET TEXT. Omitted entirely when you leave the field empty.",
    conditional: true,
  },
  {
    id: "target",
    label: "TARGET TEXT",
    detail: "The translation being corrected.",
  },
]
