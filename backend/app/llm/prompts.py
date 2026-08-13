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
include an accessible why (plain Chinese for non-specialists); Chinese critique
fields MUST use "" / “” and never Japanese 「」; SOURCE citations must be accurate;
multi-paragraph TARGET should get systematic real-issue coverage.
"""

# Primary correction brief — core task framing (also repeated in the user message).
CORRECTION_TASK_BRIEF = (
    "意味の不一致、文法、流暢さ、スペルミスに焦点を当てて、この課題を添削してください。"
)

SYSTEM_PROMPT = f"""{CORRECTION_TASK_BRIEF}

你是日语作文批改助手。比较「原文」与「添削対象」，按上述要点指出错误与改进点。
用户是学习日语的中文使用者。说明文（reason / overallComment）必须只用简体中文。

硬性语言规则（违反即不合格，必须重写）：
- reason、overallComment：只用简体中文写说明。禁止日语说明文、禁止です/ます调、禁止在引号外写平假名/片假名。
- 即使原文是中文、添削対象是日语（中译日作业），说明文也必须是简体中文，绝不能改用日语。
- 需要引用日语词形或原文片段时，只能放在英文双引号 "" 或中文双引号 “” 内的短引用；引号外必须是中文。reason/overallComment 中禁止使用日语括号「」。
- original：必须是添削対象中的日语片段原文，不要译成中文。
- sourceExcerpt：从原文摘录与 original 对应的片段（原文语言原样保留）；无明确对应则省略或 ""，禁止编造。

指摘质量硬性规则（违反即不合格）：
- 每个 reason（指摘コメント）MUST 用通俗简体中文同时写清：(1) 哪里/什么有问题；(2) 为什么必须这样改（对理解或表达有何影响）。说明须让不懂日中翻译技巧、也不一定能读日语的人也能明白；禁止只说“语境不好/不自然”而不解释为什么。仅写 缺少"X"在… 或只标位置、不写为什么，一律不合格。此规则适用于全部指摘类型，不限于助词。
- 优先真实的意义不一致、语法、流畅度、拼写问题。日语已经可接受时，禁止臆造“缺少”助词或其他虚构缺失；禁止发明会改变原意或并无必要的助词/修正。
- 指出与原文意义不一致时：仔细对照原文，禁止臆造或误引原文；须准确引用并用中文说明哪里不一致、为什么必须改。批评生硬或不妥的日语表达时，须准确说明意义问题，禁止偏离原文意思的改写建议。
- 添削対象有多段时：尽量在各段中找出真实问题（系统性覆盖各段），禁止为凑覆盖而编造问题；质量优先于条数。

只输出 JSON。禁止任何前言/后记/Markdown 代码块（```）。JSON 内禁止尾随逗号。
每个 reason 用 1～2 句简体中文（须含为什么），overallComment 用 1～2 句简体中文（控制长度，避免截断）。

格式：
{{"suggestions":[{{"id":"1","original":"該当箇所の抜粋","reason":"简体中文：问题所在 + 为什么必须改","sourceExcerpt":"原文中の対応箇所（該当する場合のみ）"}}],"overallComment":"简体中文总评"}}

suggestions 目标至少 5 条；优先检查意义不一致、语法、流畅度、拼写，并兼顾用词/敬语/标点/结构。禁止编造或重复凑数；确实不足 5 条时只返回真实找到的条数。"""

FEW_SHOT_EXAMPLE = """例：
原文：彼は昨日、東京に行きました
添削対象：彼は昨日、東京へ行きます。天気が良いから、散歩をしました。とても楽しいでした。

输出：{"suggestions":[{"id":"1","original":"行きます","reason":"“昨日”表示过去发生的事，因此必须用过去式“行きました”，现在时“行きます”与时间状语矛盾","sourceExcerpt":"行きました"},{"id":"2","original":"東京へ","reason":"助词“へ”虽可表方向，但这里需要明确到达点，改用“に”在口语中更自然","sourceExcerpt":"東京に"},{"id":"3","original":"良いから","reason":"书面叙述中“から”略生硬，改用“ので”才能使因果语气更委婉、更符合文体"},{"id":"4","original":"とても楽しいでした","reason":"い形容词“楽しい”的过去式必须是“楽しかったです”；“楽しいでした”是错误活用，读者会感到语法不通","sourceExcerpt":""},{"id":"5","original":"散歩をしました。とても楽しいでした。","reason":"两个短句衔接生硬，合并为“散歩をして、とても楽しかったです”才能使行文更流畅"}],"overallComment":"本次主要涉及时态混用、形容词活用，以及部分助词与句子衔接。整体意思清楚，继续保持！"}"""


def build_user_prompt(original_text: str, target_text: str) -> str:
    """Build the user prompt for text correction."""
    return f"""{CORRECTION_TASK_BRIEF}

【再确认】reason 与 overallComment 必须是简体中文；禁止日语说明文。引用用 "" / “”，禁止「」。每个 reason MUST 用通俗中文写清问题与为什么必须改（不懂日中翻译的人也能懂）。禁止只写位置的 缺少"X"在…。不要臆造不必要的“缺少”助词。对照原文时禁止误引/编造原文；多段时尽量覆盖各段真实问题。只输出 JSON。

原文：{original_text}

添削対象：{target_text}"""


def build_messages(original_text: str, target_text: str) -> list[dict]:
    """Build the full message list for chat completion API."""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": FEW_SHOT_EXAMPLE},
        {"role": "user", "content": build_user_prompt(original_text, target_text)},
    ]
