/**
 * Guards the claim the prompt settings dialog makes to the operator.
 *
 * The dialog renders PROMPT_COMPOSITION_STEPS as "this is where your text goes".
 * That is only trustworthy if the builders actually assemble in that order, so
 * these tests drive the real builder with marker strings and check the markers
 * come out in the declared sequence. Reorder buildPrompt and this fails naming
 * the step. The backend half of the same guarantee lives in
 * backend/tests/test_prompt_composition_order.py.
 */
import { buildPrompt } from "../prompt";
import { OUTPUT_CONTRACT } from "../prompts";
import { PROMPT_COMPOSITION_STEPS } from "@/lib/promptComposition";

const OVERRIDE = "OPERATOR_RULES_MARKER";
const SOURCE = "SOURCE_MARKER";
const EXEMPLAR = "EXEMPLAR_MARKER";
const TARGET = "TARGET_MARKER";

// A distinctive fragment of each step, to locate it in the assembled prompt.
const MARKERS: Record<string, string> = {
  body: OVERRIDE,
  "exemplar-rules": "MUST仍以原文为判断依据",
  contract: OUTPUT_CONTRACT,
  "few-shot": '输出：{"suggestions"',
  source: SOURCE,
  exemplar: EXEMPLAR,
  target: TARGET,
};

describe("PROMPT_COMPOSITION_STEPS matches what buildPrompt assembles", () => {
  it("declares a marker for every step, so nothing is silently unchecked", () => {
    for (const step of PROMPT_COMPOSITION_STEPS) {
      expect(MARKERS[step.id]).toBeDefined();
    }
  });

  it("places every step in the declared order when an exemplar is supplied", () => {
    const prompt = buildPrompt({
      originalText: SOURCE,
      targetText: TARGET,
      exemplarTranslation: EXEMPLAR,
      systemPromptOverride: OVERRIDE,
    });

    let previousOffset = -1;
    let previousLabel = "(start)";
    for (const step of PROMPT_COMPOSITION_STEPS) {
      const offset = prompt.indexOf(MARKERS[step.id]);
      expect(offset).not.toBe(-1);
      if (offset <= previousOffset) {
        throw new Error(
          `step "${step.label}" is assembled before "${previousLabel}", ` +
            "but PROMPT_COMPOSITION_STEPS tells the operator it comes after",
        );
      }
      previousOffset = offset;
      previousLabel = step.label;
    }
  });

  it("withholds exactly the conditional steps when no exemplar is supplied", () => {
    const prompt = buildPrompt({
      originalText: SOURCE,
      targetText: TARGET,
      systemPromptOverride: OVERRIDE,
    });

    for (const step of PROMPT_COMPOSITION_STEPS) {
      const present = prompt.includes(MARKERS[step.id]);
      if (step.conditional) {
        expect(present).toBe(false);
      } else {
        expect(present).toBe(true);
      }
    }
  });
});
