/**
 * Prompt construction for WebLLM inference
 * 
 * Prompts are imported from ./prompts/ for easy management and optimization.
 * Edit those files to modify AI behavior without touching this engine code.
 */

import {
  SYSTEM_PROMPT,
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
};

/**
 * Build the complete prompt for WebLLM chat completion
 * Uses imported templates from ./prompts/ for easy management
 */
export function buildPrompt(input: PromptInput): string {
  const exemplar = (input.exemplarTranslation || "").trim();

  let prompt = SYSTEM_PROMPT;
  if (exemplar) {
    prompt += "\n" + EXEMPLAR_REFERENCE_RULES;
  }
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
