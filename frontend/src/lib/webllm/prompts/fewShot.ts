/**
 * Few-shot example for WebLLM inference (SmolLM2-optimized)
 * 
 * Minimal example showing:
 * - Expected JSON structure (no trailing commas!)
 * - Correct output format (raw JSON, no markdown fences)
 * Kept ultra-short to reduce prompt tokens.
 */
export const FEW_SHOT_EXAMPLES = `例：原文「答えようがありませんでした」译文「我并不想回复」
输出：{"指摘":[{"番号":1,"箇所":"我并不想回复","コメント":"ようがない是无法，非不想"}],"全体講評":"OK"}`;
