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
 * - Gemini quality bar + teaching bar: natural Chinese reasons with
 *   contrastive 旧形 → 「新形」 inside prose (not 现状：/推荐： labels);
 *   overallComment strengths→gaps.
 * Kept ultra-short to reduce prompt tokens.
 * Works with Mistral 7B (current), SmolLM2, and other instruct models.
 */
export const FEW_SHOT_EXAMPLES = `例：原文“现代人阅读史诗……”添削対象「現代人が史詩を読む。でも、史詩はまず声である。」
输出：{"suggestions":[{"id":"1","original":"史詩","reason":"「史詩」像未消化的中文词形，宜改为「叙事詩」（じょじし）：日语社科/文学里“史诗”的规范译词是「叙事詩」。混用暴露领域译词基础不足，今后也易写错","sourceExcerpt":"史诗"},{"id":"2","original":"でも、","reason":"「でも」偏口语会话转折，宜改为「しかし」：后者偏书面论述。学术随笔开篇应用后者，否则语域偏低"},{"id":"3","original":"史詩はまず声である","reason":"「史詩はまず声である」可改为「叙事詩はまず声である」：与规范译词一致，并保留“首先是声音”的对比。译词基础不足会连带整句专名继续写错"}],"overallComment":"已传达史诗首先是声音这一对比。主要问题是规范译词与语域。"}`;
