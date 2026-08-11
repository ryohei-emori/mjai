/**
 * Few-shot example for WebLLM inference
 * 
 * Minimal example showing:
 * - Expected JSON structure (no trailing commas!)
 * - Correct output format (raw JSON, no markdown fences)
 * - Uses English keys as canonical schema (per AGENTS.md)
 * Kept ultra-short to reduce prompt tokens.
 * Works with Mistral 7B (current), SmolLM2, and other instruct models.
 */
export const FEW_SHOT_EXAMPLES = `例：原文「答えようがありませんでした」译文「我并不想回复」
输出：{"suggestions":[{"id":"1","original":"我并不想回复","reason":"ようがない是无法，非不想"}],"overallComment":"OK"}`;
