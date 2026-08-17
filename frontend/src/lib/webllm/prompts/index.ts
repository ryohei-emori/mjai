/**
 * WebLLM Prompts
 * 
 * This module exports all prompt templates for WebLLM inference.
 * Edit these files to modify AI correction behavior:
 * 
 * - system.ts: Core instructions for the AI proofreader
 * - fewShot.ts: Example showing expected JSON output format
 * - templates.ts: Section headers used in prompt construction
 * 
 * Changes here do NOT require a backend deploy - only frontend rebuild.
 */

export {
  SYSTEM_PROMPT,
  SYSTEM_PROMPT_HEAD,
  SYSTEM_PROMPT_TAIL,
  OUTPUT_CONTRACT,
  EXEMPLAR_REFERENCE_RULES,
} from './system';
export { FEW_SHOT_EXAMPLES } from './fewShot';
export {
  SECTION_ORIGINAL,
  SECTION_EXEMPLAR,
  SECTION_TARGET,
  SECTION_INSTRUCTION,
  SECTION_ANSWER,
  SECTION_ERROR_POINTING,
  SECTION_PROBLEM,
} from './templates';
