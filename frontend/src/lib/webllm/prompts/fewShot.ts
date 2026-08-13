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
 * - Optional "sourceExcerpt" field (2026-08, `highlight-suggestion-text-spans`
 *   change): demonstrates both a present case (id "1", a corresponding
 *   excerpt exists in 原文) and an absent case (id "2", omitted — helper
 *   particle usage has no direct 原文 counterpart to point to).
 * - Chinese critique cites use “” (never 「」) per
 *   `harden-semantic-suggestion-reasons`.
 * Kept ultra-short to reduce prompt tokens.
 * Works with Mistral 7B (current), SmolLM2, and other instruct models.
 */
export const FEW_SHOT_EXAMPLES = `例：原文「彼は昨日、東京に行きました」添削対象「彼は昨日、東京へ行きます」
输出：{"suggestions":[{"id":"1","original":"行きます","reason":"“昨日”是过去的事，因此必须用过去式“行きました”","sourceExcerpt":"行きました"},{"id":"2","original":"へ","reason":"这里需要明确到达点，改用“に”在口语中才更自然"}],"overallComment":"存在时态和助词使用问题"}`;
