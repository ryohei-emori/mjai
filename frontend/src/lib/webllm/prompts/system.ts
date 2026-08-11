/**
 * System prompt for WebLLM inference
 * 
 * Optimized for structured JSON output:
 * - Ultra-concise, direct instructions
 * - Explicit JSON-only output requirement
 * - Explicit prohibitions: no trailing commas, no markdown fences, no commentary
 * - Uses English keys as canonical schema (per AGENTS.md)
 * - Field-level language split (2026-08, matches backend/app/llm/prompts.py):
 *   "original" stays in the source/corrected text's own language (Japanese
 *   for this app's actual usage), while "reason"/"overallComment" are
 *   Chinese explanations for this app's Chinese-speaking users.
 * - Suggestion count target: at least 5 genuine issues (2026-08, reversed
 *   from an earlier "up to 3" cap) — see AGENTS.md and
 *   openspec/changes/add-groq-cloudflare-suggestions/specs/ai-suggestions/spec.md
 * 
 * Works with Mistral 7B (current), SmolLM2, and other instruct models.
 */
export const SYSTEM_PROMPT = `翻译校对。只输出JSON，禁止其他文字。禁止\`\`\`。禁止尾随逗号。

格式：{"suggestions":[{"id":"1","original":"日语原文片段","reason":"中文建议"}],"overallComment":"中文总评"}
original字段保留原语言（日语），禁止翻译成中文。reason和overallComment必须用中文。
至少5条suggestions，从用词、语气、标点、语序、结构等角度尽量找出问题，不要过早停止。确实找不到5条时才可少于5条，禁止编造凑数。`;
