/**
 * System prompt for WebLLM inference
 * 
 * Optimized for structured JSON output:
 * - Ultra-concise, direct instructions
 * - Explicit JSON-only output requirement
 * - Explicit prohibitions: no trailing commas, no markdown fences, no commentary
 * - Uses English keys as canonical schema (per AGENTS.md)
 * 
 * Works with Mistral 7B (current), SmolLM2, and other instruct models.
 */
export const SYSTEM_PROMPT = `翻译校对。只输出JSON，禁止其他文字。禁止\`\`\`。禁止尾随逗号。

格式：{"suggestions":[{"id":"1","original":"片段","reason":"建议"}],"overallComment":"总评"}
最多5条suggestions。`;
