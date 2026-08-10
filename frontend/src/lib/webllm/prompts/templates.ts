/**
 * Template sections for constructing prompts
 * 
 * These constants define the section headers and structure
 * used in buildPrompt(). Keeping them separate allows:
 * - Consistent formatting across prompts
 * - Easy modification of section wording
 * - Potential future localization
 */

/** Section header for the original text (source language) */
export const SECTION_ORIGINAL = '＜中国語または日本語に翻訳する日本語または中国語の文＞';

/** Section header for the target text (translation attempt) */
export const SECTION_TARGET = '＜日本語または中国語の文から中国語または日本語に翻訳を試みた文＞';

/** Section header for additional instructions */
export const SECTION_INSTRUCTION = '## 追加指示';

/** Section header marking where the AI should respond */
export const SECTION_ANSWER = '## あなたが生成する回答';

/** Section header for the error pointing response */
export const SECTION_ERROR_POINTING = '＜日本語または中国語の文から中国語または日本語に翻訳を試みた文に対する誤りの指摘＞';

/** Section header for the problem statement */
export const SECTION_PROBLEM = '## 問題';
