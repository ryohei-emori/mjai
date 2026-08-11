/**
 * Few-shot example for WebLLM inference
 * 
 * Minimal example showing:
 * - Expected JSON structure (no trailing commas!)
 * - Correct output format (raw JSON, no markdown fences)
 * - Uses English keys as canonical schema (per AGENTS.md)
 * - Field-level language split (2026-08): "original" stays in Japanese
 *   (the actual corrected-text content), "reason"/"overallComment" are
 *   Chinese explanations for this app's Chinese-speaking users.
 * Kept ultra-short to reduce prompt tokens.
 * Works with Mistral 7B (current), SmolLM2, and other instruct models.
 */
export const FEW_SHOT_EXAMPLES = `例：原文「彼は昨日、東京に行きました」添削対象「彼は昨日、東京へ行きます」
输出：{"suggestions":[{"id":"1","original":"行きます","reason":"「昨日」是过去的事，应使用过去式「行きました」"},{"id":"2","original":"へ","reason":"「に」在口语中更自然，能明确表达到达点"}],"overallComment":"存在时态和助词使用问题"}`;
