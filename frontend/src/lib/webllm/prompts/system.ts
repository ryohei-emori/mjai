/**
 * System prompt for WebLLM inference
 * 
 * Optimized for structured JSON output:
 * - Ultra-concise, direct instructions
 * - Explicit JSON-only output requirement
 * - Explicit prohibitions: no trailing commas, no markdown fences, no commentary
 * 
 * Works with Mistral 7B (current), SmolLM2, and other instruct models.
 */
export const SYSTEM_PROMPT = `翻译校对。只输出JSON，禁止其他文字。禁止\`\`\`。禁止尾随逗号。

格式：{"指摘":[{"番号":1,"箇所":"片段","コメント":"建议"}],"全体講評":"总评"}
最多5条指摘。`;
