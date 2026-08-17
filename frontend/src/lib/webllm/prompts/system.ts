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
 * - Spec MUST why-in-reason + anti-false-缺少 + accessibility + SOURCE
 *   fidelity + multi-paragraph coverage
 *   (`harden-semantic-suggestion-reasons`).
 * - Gemini quality bar (`raise-suggestion-quality-to-gemini-bar`): overallComment
 *   strengths→gaps; reason problem→fix→why in natural Chinese; CN→JP
 *   literary/academic; 「」 only for JP TARGET cites, ""/“” for Chinese meta.
 * - Teaching bar (`improve-suggestion-teaching-quality`): essential competence
 *   gaps; anti trivial-surface / anti bare source-token-swap; contrastive
 *   nuance before lexical preference; class-of-error why for future translations.
 * - Format/coverage (`fix-critique-format-and-gemini-coverage`): no forced
 *   spoken labels 现状：/推荐：/現状：/推奨：; do not stop after ~2 real issues.
 * - Coherence pass (`refine-prompt-instruction-coherence`): coverage guidance
 *   stated once instead of duplicated across lines (7B instruction budget);
 *   anti-padding no longer doubles as licence to under-report; per-item length
 *   bound replaces a global brevity cue; explicit note that a JP-internal
 *   grammar fault has no 原文 counterpart so `sourceExcerpt` is omitted.
 * - Target-language critique (`editable-prompt-model-log-and-critique-fix`):
 *   recommended forms must be written in Japanese (a reported cloud session
 *   returned Chinese words as the correction), only 添削対象 may be corrected,
 *   interchangeable synonyms are not faults, and a proposed form must be
 *   substituted into the sentence and checked. Condensed to two lines for the
 *   7B budget; see backend/app/llm/prompts.py for the full rules.
 * - Optional exemplar (`add-optional-exemplar-translation-input`): when the
 *   user pastes a 模範回答訳文, EXEMPLAR_REFERENCE_RULES is appended to this
 *   prompt and the exemplar gets its own labeled section. Both are withheld
 *   when the field is empty, so the offline prompt is unchanged for users who
 *   do not have an exemplar — and a 7B model is never told about a section
 *   that is not in its context. Kept to two lines because the backend's
 *   five-line version would eat a noticeable slice of the 7B instruction
 *   budget; see backend/app/llm/prompts.py for the live A/B evidence behind
 *   the guard's content.
 * 
 * Works with Mistral 7B (current), SmolLM2, and other instruct models.
 *
 * Split into three parts (`revise-system-prompt-settings-ui`, 2026-08) so a
 * stored shared prompt can replace the *rules* without taking the machine
 * interface with it. `SYSTEM_PROMPT` reassembles them in their original order,
 * byte-for-byte, so the offline default is unchanged; an override composes as
 * `override + OUTPUT_CONTRACT` instead (see prompt.ts `buildSystemPrompt`).
 *
 * The contract is spliced into the *middle* of the default rather than
 * appended, unlike the backend's `OUTPUT_CONTRACT`, because that is where this
 * prompt was tuned and measured with it. Moving it to the end to match the
 * backend's shape would silently change the prompt every offline user without a
 * custom prompt receives — the one thing this split is meant not to do.
 */

/** Task framing, ahead of the output contract. */
export const SYSTEM_PROMPT_HEAD = `意味の不一致、文法、流暢さ、スペルミスに焦点を当てて、この課題を添削してください。
中译日文学/学术翻译校对。`;

/**
 * Machine-interface contract: JSON-only, the response schema, and the
 * field-language rule that keeps `original` / `sourceExcerpt` Japanese.
 * Always supplied by code — a stored prompt can lower critique quality but
 * cannot remove the response contract. Mirrors `OUTPUT_CONTRACT` in
 * backend/app/llm/prompts.py.
 */
export const OUTPUT_CONTRACT = `只输出JSON，禁止其他文字。禁止\`\`\`。禁止尾随逗号。

格式：{"suggestions":[{"id":"1","original":"日语原文片段","reason":"自然简体中文：问题、推荐日语形（如有）、为什么必须改","sourceExcerpt":"原文中对应片段（如有）"}],"overallComment":"先肯定优点，再概括问题"}
original/sourceExcerpt保留日语，禁止译成中文。`;

/** Built-in critique rules; this is the part a stored prompt replaces. */
export const SYSTEM_PROMPT_TAIL = `reason和overallComment必须是简体中文：禁止日语说明/假名（引号外）。中文引用用""或“”；日语词形可用「」；禁止用「」包中文说明词（如「时态」）。违反即不合格。
overallComment MUST先写优点再写问题。每个reason MUST用自然通俗中文写清(1)当前译法问题(2)有改法时给推荐日语形（可用 旧形 → 「新形」 嵌入句中）(3)为什么必须改（尽量点明对今后翻译能力的影响）；不懂日中翻译也能懂；每条约2–4句，禁止只说“不好/不自然”；禁止只写缺少"X"在…。禁止强制「现状：」「推荐：」「現状：」「推奨：」等冒号标签口播。reason只写给学习者看的讲评，不要写给模型的元指令。日语已可接受时禁止臆造缺少助词。
教学硬性：优先实质问题（意义偏移、系统语法、暴露词基不足的拼写、语域/领域误用、情态错位、数字·单位的日语写法等）。禁止把可省略的表面简化当主指摘。禁止无教学的“跟原文对词”。词汇升级须先对比当前词与推荐词语感/语义，再说明为何推荐。
推荐形必须用日语写出：禁止把中文词当成修正后的形（反例：改为"理论上"、改为"对比"）。只添削「添削対象」，原文是判断依据、不是添削对象。可互换的近义替换（比較⇄対比、研究者⇄学者）不算错误；提推荐形前必须代入原句确认语法与搭配自然（反例：「睡眠が需要だ」不成立）。
对照原文时禁止误引或编造原文；批评生硬日语时勿偏离原文意思。关注规范译词、语域、中式日语→自然日语等。
sourceExcerpt可选：从原文摘录与original对应的片段；无明确对应则省略或""，禁止编造。日语内部的语法/活用错误在原文里常常没有对应片段，这时就省略。
至少5条suggestions（多段时MUST逐段扫描覆盖各段真实问题，长文应明显更多）；优先检查意义不一致、语法、流畅度、拼写，并兼顾用词/语气/标点/结构；禁止只写1–2条就提前结束；禁止编造或拆分同一问题来凑数，但“不许凑数”不等于可以少报，真实问题必须全写出来；确实不足5条才可更少。`;

/**
 * The built-in offline prompt: the three parts above in their original order.
 * Used verbatim whenever no shared prompt is stored.
 */
export const SYSTEM_PROMPT = `${SYSTEM_PROMPT_HEAD}${OUTPUT_CONTRACT}
${SYSTEM_PROMPT_TAIL}`;

/**
 * Appended to SYSTEM_PROMPT only when a non-empty 模範回答訳文 is supplied.
 *
 * Mirrors backend/app/llm/prompts.py EXEMPLAR_REFERENCE_RULES, condensed for
 * the 7B instruction budget. The two clauses that must survive condensing are
 * "still judge against 原文" and "never cite the exemplar as the reason" —
 * without them a pasted reference measurably reduces issue coverage.
 */
export const EXEMPLAR_REFERENCE_RULES = `模範回答訳文（如有）只是参考译文，用来校准原文意图、语域与译词范围；不是评分标准，也不是要把添削対象改写成它。MUST仍以原文为判断依据；禁止把“与参考译文不同”本身当成问题，添削対象另有同样准确自然的写法时不得指为错误。
禁止在reason/overallComment里提及参考译文（禁止出现“参考译文”“模範回答”“参考訳”字样）；推荐改法必须用语言学理由说明为什么必须改，“参考译文这么写”不是理由。`;
