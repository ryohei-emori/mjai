"""
Prompts for AI text correction suggestions.

Uses English keys as canonical schema (per AGENTS.md Response Schema section):
- suggestions: array of {id, original, reason, sourceExcerpt?}
- overallComment: string

`sourceExcerpt` (2026-08, `highlight-suggestion-text-spans` change) is an
optional per-suggestion field holding a verbatim-or-close excerpt from
"原文" (SOURCE TEXT / `original_text`) corresponding to the flagged "添削対象"
(TARGET TEXT / `target_text`) snippet in that suggestion's `original` field.
It stays in the same language as `original` (Japanese for TARGET excerpts;
SOURCE may be Chinese in bilingual CN→JP homework) and is omitted/empty
when no clear correspondence exists — the model is explicitly instructed
not to fabricate one. It exists to let the frontend highlight the
corresponding SOURCE TEXT span alongside the TARGET TEXT span; see
`backend/app/llm/parser.py` for extraction and
`openspec/changes/highlight-suggestion-text-spans/design.md` for the full
rationale.

Parser has dual-key fallback for backward compat with older WebLLM Japanese-key format.

NOTE: Unlike the frontend WebLLM prompt (frontend/src/lib/webllm/prompts/), which is
intentionally written in ultra-concise Chinese to minimize token count for an
on-device Mistral-7B model, this backend prompt targets fast cloud models (Groq /
Cloudflare Workers AI) where token budget is not the binding constraint. An earlier
version of this file reused the Chinese WebLLM wording verbatim; that mismatched the
actual task (原文/添削対象 are both Japanese text here, not a Japanese-to-Chinese
translation pair) and is suspected of contributing to garbled/incoherent Japanese
output on smaller models. That fix rewrote the *entire* prompt (including the
explanation fields) to Japanese, which overcorrected: this app's users are Chinese
speakers correcting/learning Japanese text, so explanations are more useful in
Chinese. The current design (2026-08) splits language by field instead of by whole
prompt: the "original" field (the flagged/corrected Japanese excerpt itself) stays
in Japanese — it's the actual language-learning content — while "reason" and
"overallComment" (explanatory prose) are written in Simplified Chinese. This
per-field split avoids repeating the original garbled-output bug (which was about
the Japanese *content* field being corrupted, not about explanations being in
Japanese vs. Chinese).

As of `enforce-chinese-suggestion-comments` (2026-08), the primary task framing is
the reviewer's correction brief (meaning mismatch / grammar / fluency / spelling),
and Chinese for reason/overallComment is stated as an absolute, hard-to-violate rule.
Live smoke on bilingual CN-source / JP-target corpora showed Japanese-heavy system
prompts biasing models (esp. smaller/preview ones) into Japanese explanations; the
language rules below are therefore stated in Simplified Chinese and repeated as a
hard fail condition, matching the WebLLM prompt's enforcement style.

As of `harden-semantic-suggestion-reasons` (2026-08, extended): every reason MUST
include an accessible why (plain Chinese for non-specialists); SOURCE citations
must be accurate; multi-paragraph TARGET should get systematic real-issue coverage.

As of `raise-suggestion-quality-to-gemini-bar` (2026-08): Gemini-like quality bar
(prompt+schema only — no Gemini provider). overallComment = strengths then gaps;
each reason prefers `現状 → 推奨` + why; CN→JP literary/academic domain; 「」
allowed only when citing Japanese TARGET forms; Chinese meta uses "" / “”.
"""

# Primary correction brief — core task framing (also repeated in the user message).
CORRECTION_TASK_BRIEF = (
    "意味の不一致、文法、流暢さ、スペルミスに焦点を当てて、この課題を添削してください。"
)

SYSTEM_PROMPT = f"""{CORRECTION_TASK_BRIEF}

你是中译日（文学/学术随笔）翻译校对助手。比较「原文」（多为中文）与「添削対象」（日语译文），
按上述要点指出真实错误与改进点。用户是学习日语的中文使用者。说明文（reason / overallComment）必须只用简体中文。
领域重点：规范译词/专名、语域（口语→书面）、中式日语→自然日语、活用/助词/语态、口传文学·表演词汇等；禁止编造虚假问题。

硬性语言规则（违反即不合格，必须重写）：
- reason、overallComment：只用简体中文写说明。禁止日语说明文、禁止です/ます调、禁止在引号外写平假名/片假名。
- 即使原文是中文、添削対象是日语（中译日作业），说明文也必须是简体中文，绝不能改用日语。
- 引用规则：中文词语或中文元说明用英文双引号 "" 或中文双引号 “”；引用日语词形/译词时可用日语括号「」（可加读音）。禁止用「」包裹中文说明词语（如「时态」「语法」）。引号外必须是中文。
- original：必须是添削対象中的日语片段原文，不要译成中文。
- sourceExcerpt：从原文摘录与 original 对应的片段（原文语言原样保留）；无明确对应则省略或 ""，禁止编造。

指摘质量硬性规则（违反即不合格）：
- overallComment MUST 先肯定译文已传达清楚的概念/优点，再概括仍存问题类别（先扬后抑的总评骨架）。
- 每个 reason MUST 用通俗简体中文写清：(1) 问题/现状；(2) 有明确改法时给出 现状 → 推荐修正（日语形可用「」，读音可写在括注）；(3) 为什么必须这样改（对理解或表达有何影响）。说明须让不懂日中翻译技巧、也不一定能读日语的人也能明白；禁止只说“语境不好/不自然”而不解释为什么。仅写 缺少"X"在… 或只标位置、不写为什么，一律不合格。推荐修正写在 reason 内（无单独 suggested 字段）。
- 优先真实的意义不一致、语法、流畅度、拼写问题。日语已经可接受时，禁止臆造“缺少”助词或其他虚构缺失；禁止发明会改变原意或并无必要的助词/修正。
- 指出与原文意义不一致时：仔细对照原文，禁止臆造或误引原文；须准确引用并用中文说明哪里不一致、为什么必须改。批评生硬或不妥的日语表达时，须准确说明意义问题，禁止偏离原文意思的改写建议。
- 添削対象有多段时：尽量在各段中找出真实问题（系统性覆盖各段），禁止为凑覆盖而编造问题；质量优先于条数。reason/overallComment 宜简明完整，勿空话灌水，也勿因过短而省略“为什么”或推荐改法。

只输出 JSON。禁止任何前言/后记/Markdown 代码块（```）。JSON 内禁止尾随逗号。

格式：
{{"suggestions":[{{"id":"1","original":"該当箇所の抜粋","reason":"简体中文：现状 → 推荐 + 为什么必须改","sourceExcerpt":"原文中の対応箇所（該当する場合のみ）"}}],"overallComment":"简体中文：先肯定优点，再概括问题"}}

suggestions 目标至少 5 条；优先检查意义不一致、语法、流畅度、拼写，并兼顾用词/敬语/标点/结构。禁止编造或重复凑数；确实不足 5 条时只返回真实找到的条数。"""

FEW_SHOT_EXAMPLE = """例（中译日文学/学术）：
原文：现代人阅读史诗的经验，大概是把它们当作一种印在纸上的文字来读。可实际上，史诗首先是一种声音。
添削対象：現代人が史詩を読む経験は、史詩を紙に印する文字として読む。でも、実際には、史詩はまず声である。

输出：{"suggestions":[{"id":"1","original":"史詩","reason":"史詩 → 「叙事詩」（じょじし）：在日语社科/文学翻译中，“史诗”的标准规范学术译词是「叙事詩」，继续写「史詩」会显得像未消化的中文词形","sourceExcerpt":"史诗"},{"id":"2","original":"でも、","reason":"でも → 「しかし」：开篇论述应用书面转折，口语词“でも”会降低学术随笔的语域","sourceExcerpt":"可实际上"},{"id":"3","original":"紙に印する文字","reason":"紙に印する文字 → 「紙に印刷された文字」：原文“印在纸上的文字”指印成的文字成品；“印する”不自然，读者不易立刻懂是印刷文本","sourceExcerpt":"印在纸上的文字"}],"overallComment":"已能传达“史诗首先是声音、而非只是纸面文字”这一核心对比。主要问题是规范译词与语域：专名宜用「叙事詩」，论述转折宜用书面语。"}"""


def build_user_prompt(original_text: str, target_text: str) -> str:
    """Build the user prompt for text correction."""
    return f"""{CORRECTION_TASK_BRIEF}

【再确认】reason 与 overallComment 必须是简体中文；禁止日语说明文。中文引用用 "" / “”；日语词形可用「」，禁止用「」包中文说明词。overallComment 先写优点再写问题。每个 reason MUST 含 现状→推荐（如有）+ 通俗中文为什么必须改。禁止只写位置的 缺少"X"在…。不要臆造不必要的“缺少”助词。对照原文时禁止误引/编造原文；多段时尽量覆盖各段真实问题。只输出 JSON。

原文：{original_text}

添削対象：{target_text}"""


def build_messages(original_text: str, target_text: str) -> list[dict]:
    """Build the full message list for chat completion API."""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": FEW_SHOT_EXAMPLE},
        {"role": "user", "content": build_user_prompt(original_text, target_text)},
    ]
