/**
 * Few-shot example for WebLLM inference (SmolLM2-optimized)
 * 
 * Minimal example showing:
 * - Expected JSON structure
 * - Correct output format
 * Kept short to reduce prompt tokens and improve inference speed.
 */
export const FEW_SHOT_EXAMPLES = `
## 例
原文：答えようがありませんでした。
译文：我并不想回复。

输出：
{"指摘":[{"番号":1,"箇所":"我并不想回复","コメント":"ようがない表示无法回答，非不想回答"}],"全体講評":"注意文法含义，加油〜"}
`;
