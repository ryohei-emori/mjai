/**
 * System prompt for WebLLM inference
 * 
 * Optimized for structured JSON output:
 * - Ultra-concise, direct instructions
 * - Explicit JSON-only output requirement
 * - Explicit prohibitions: no trailing commas, no markdown fences, no commentary
 * - Uses English keys as canonical schema (per AGENTS.md)
 * - Primary task framing: meaning mismatch / grammar / fluency / spelling
 *   (enforce-chinese-suggestion-comments, 2026-08)
 * - Field-level language split (2026-08, matches backend/app/llm/prompts.py):
 *   "original" stays in the source/corrected text's own language (Japanese
 *   for this app's actual usage), while "reason"/"overallComment" are
 *   Chinese explanations for this app's Chinese-speaking users.
 * - Suggestion count target: at least 5 genuine issues (2026-08, reversed
 *   from an earlier "up to 3" cap) — see AGENTS.md and
 *   openspec/changes/add-groq-cloudflare-suggestions/specs/ai-suggestions/spec.md
 * - Optional "sourceExcerpt" field (2026-08, `highlight-suggestion-text-spans`
 *   change, mirrors backend/app/llm/prompts.py): excerpt from the SOURCE
 *   TEXT corresponding to the flagged TARGET TEXT snippet, same language
 *   rule as "original" (stays Japanese), omitted/empty when no clear
 *   correspondence exists — never fabricated.
 * 
 * Works with Mistral 7B (current), SmolLM2, and other instruct models.
 */
export const SYSTEM_PROMPT = `意味の不一致、文法、流暢さ、スペルミスに焦点を当てて、この課題を添削してください。
翻译校对。只输出JSON，禁止其他文字。禁止\`\`\`。禁止尾随逗号。

格式：{"suggestions":[{"id":"1","original":"日语原文片段","reason":"简体中文建议","sourceExcerpt":"原文中对应片段（如有）"}],"overallComment":"简体中文总评"}
original/sourceExcerpt保留日语，禁止译成中文。
reason和overallComment必须是简体中文：禁止日语、禁止假名、禁止日语助词/说明。违反即不合格。
sourceExcerpt可选：从原文摘录与original对应的日语片段；无明确对应则省略或""，禁止编造。
至少5条suggestions，优先检查意义不一致、语法、流畅度、拼写，并兼顾用词/语气/标点/结构；确实不足5条才可更少，禁止编造凑数。`;
