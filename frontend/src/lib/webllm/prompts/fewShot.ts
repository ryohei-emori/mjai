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
 * - Coherence pass (`refine-prompt-instruction-coherence`): the old third item
 *   restated the first item's 史詩→叙事詩 correction, which modelled exactly the
 *   padding-by-repetition the system prompt forbids. It is replaced by a
 *   distinct meaning/modality omission so the example also demonstrates the
 *   highest-priority issue category, not lexical and register items only. A
 *   note states the item count tracks the short example input and is not a cap.
 * Kept ultra-short to reduce prompt tokens.
 * Works with Mistral 7B (current), SmolLM2, and other instruct models.
 */
export const FEW_SHOT_EXAMPLES = `例（示例原文很短，故只有3条；示例条数不是上限，多段长文应明显更多。第2条是日语内部问题，原文无对应片段，故省略sourceExcerpt）：原文“现代人阅读史诗的经验，大概是把它们当作一种印在纸上的文字来读……”添削対象「現代人が史詩を読む。でも、史詩はまず声である。」
输出：{"suggestions":[{"id":"1","original":"史詩","reason":"「史詩」像未消化的中文词形，宜改为「叙事詩」（じょじし）：日语社科/文学里“史诗”的规范译词是「叙事詩」。混用暴露领域译词基础不足，今后也易写错","sourceExcerpt":"史诗"},{"id":"2","original":"でも、","reason":"「でも」偏口语会话转折，宜改为「しかし」：后者偏书面论述。学术随笔开篇应用后者，否则语域偏低"},{"id":"3","original":"現代人が史詩を読む。","reason":"原文说的是“阅读史诗的经验，大概是把它们当作印在纸上的文字来读”，译文只剩“现代人读史诗”，把「経験」这个主题和“大概”的推测语气都丢了，论点强度和逻辑都变了。宜补全为「現代人が叙事詩を読む経験は、それを紙に印刷された文字として読むことだろう」。成分与情态脱落属于意义偏移，比用词不美更严重","sourceExcerpt":"现代人阅读史诗的经验，大概是把它们当作一种印在纸上的文字来读"}],"overallComment":"已传达史诗首先是声音这一对比。主要问题是规范译词、语域，以及成分与情态脱落造成的意义偏移。"}`;
