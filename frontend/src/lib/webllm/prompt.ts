/**
 * Prompt construction for WebLLM inference
 * 
 * Prompts are imported from ./prompts/ for easy management and optimization.
 * Edit those files to modify AI behavior without touching this engine code.
 */

import {
  SYSTEM_PROMPT,
  OUTPUT_CONTRACT,
  EXEMPLAR_REFERENCE_RULES,
  FEW_SHOT_EXAMPLES,
  SECTION_ORIGINAL,
  SECTION_EXEMPLAR,
  SECTION_TARGET,
  SECTION_INSTRUCTION,
  SECTION_ANSWER,
  SECTION_ERROR_POINTING,
  SECTION_PROBLEM,
} from './prompts';

export type PromptInput = {
  originalText: string;
  targetText: string;
  /**
   * Optional 模範回答訳文 — a known-good translation of `originalText` used
   * only to calibrate expected meaning/register. Empty or whitespace-only
   * values leave the prompt byte-identical to the SOURCE/TARGET-only form.
   */
  exemplarTranslation?: string;
  instructionPrompt?: string;
  /**
   * The stored shared correction prompt, when the operator has customized it.
   * Replaces the built-in rules body; the output contract and the few-shot
   * example are still supplied by code. Empty or absent keeps the built-in
   * offline prompt, which is deliberately condensed for a 7B model.
   */
  systemPromptOverride?: string;
};

/**
 * Compose the system section, mirroring `build_system_prompt` in
 * backend/app/llm/prompts.py: rules body, then the exemplar rules when an
 * exemplar was supplied, then the code-owned output contract.
 *
 * With no override the result is `SYSTEM_PROMPT` (plus the exemplar rules),
 * where the contract already sits inside the built-in text — so an offline user
 * who never customized the prompt gets exactly what they got before.
 */
export function buildSystemPrompt(
  exemplarTranslation?: string,
  systemPromptOverride?: string,
): string {
  const exemplar = (exemplarTranslation || "").trim();
  const override = (systemPromptOverride || "").trim();
  const exemplarRules = exemplar ? "\n" + EXEMPLAR_REFERENCE_RULES : "";

  if (!override) {
    return SYSTEM_PROMPT + exemplarRules;
  }
  return override + exemplarRules + "\n" + OUTPUT_CONTRACT;
}

/**
 * Build the complete prompt for WebLLM chat completion
 * Uses imported templates from ./prompts/ for easy management
 */
export function buildPrompt(input: PromptInput): string {
  const exemplar = (input.exemplarTranslation || "").trim();

  let prompt = buildSystemPrompt(
    input.exemplarTranslation,
    input.systemPromptOverride,
  );
  prompt += "\n" + FEW_SHOT_EXAMPLES + "\n";
  prompt += `${SECTION_PROBLEM}\n`;
  prompt += `${SECTION_ORIGINAL}\n${input.originalText}\n\n`;
  if (exemplar) {
    prompt += `${SECTION_EXEMPLAR}\n${exemplar}\n\n`;
  }
  prompt += `${SECTION_TARGET}\n${input.targetText}\n\n`;
  
  if (input.instructionPrompt && input.instructionPrompt.trim()) {
    prompt += `${SECTION_INSTRUCTION}\n${input.instructionPrompt}\n\n`;
  }
  
  prompt += `${SECTION_ANSWER}\n${SECTION_ERROR_POINTING}`;
  
  return prompt;
}

/**
 * Build messages array for chat completion API
 */
export function buildChatMessages(input: PromptInput): Array<{ role: "system" | "user" | "assistant"; content: string }> {
  return [
    { role: "user", content: buildPrompt(input) }
  ];
}
