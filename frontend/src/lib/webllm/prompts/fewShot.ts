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
 * - Gemini quality bar (`raise-suggestion-quality-to-gemini-bar`): “” for
 *   Chinese cites, 「」 only around Japanese forms; overallComment
 *   strengths→gaps; reason `现状 → 推荐` + why.
 * Kept ultra-short to reduce prompt tokens.
 * Works with Mistral 7B (current), SmolLM2, and other instruct models.
 */
export const FEW_SHOT_EXAMPLES = `例：原文“现代人阅读史诗……”添削対象「現代人が史詩を読む。でも、史詩はまず声である。」
输出：{"suggestions":[{"id":"1","original":"史詩","reason":"史詩 → 「叙事詩」（じょじし）：“史诗”在日语社科/文学中的规范译词是「叙事詩」","sourceExcerpt":"史诗"},{"id":"2","original":"でも、","reason":"でも → 「しかし」：论述开篇应用书面转折，口语“でも”语域偏低"}],"overallComment":"已传达史诗首先是声音这一对比。主要问题是规范译词与语域。"}`;
