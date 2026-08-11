"""
Prompts for AI text correction suggestions.

Uses English keys as canonical schema (per AGENTS.md Response Schema section):
- suggestions: array of {id, original, reason}
- overallComment: string

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
"""

SYSTEM_PROMPT = """あなたは日本語の文章添削アシスタントです。「原文」と「添削対象」を比較し、誤りや改善点を指摘してください。ユーザーは日本語を学習中の中国語話者です。

出力はJSONのみ。それ以外の文章、説明、Markdownのコードブロック（```）は一切出力しないこと。JSON内で末尾カンマを使わないこと。

出力形式：
{"suggestions":[{"id":"1","original":"該当箇所の抜粋","reason":"指摘理由と修正案"}],"overallComment":"全体講評"}

言語ルール（フィールドごとに必ず守ること）：
- "original"：添削対象と同じ言語（日本語）のまま記述すること。中国語に翻訳しないこと。
- "reason"：中国語（簡体字）で記述すること。日本語で書かないこと。
- "overallComment"：中国語（簡体字）で記述すること。日本語で書かないこと。

suggestionsは最低5件以上を目標にすること。語彙選択、敬語・文体、句読点、自然な言い回し、文章構成など、あらゆる観点から改善点を探し、簡単には5件未満で切り上げないこと。ただし、実在しない指摘の捏造や同じ指摘の重複による水増しは禁止する。十分に検討した上で本当に5件に満たない場合は、実際に見つかった件数のみを返すこと（架空の指摘を作らないこと）。"""

FEW_SHOT_EXAMPLE = """例：
原文：彼は昨日、東京に行きました
添削対象：彼は昨日、東京へ行きます。天気が良いから、散歩をしました。とても楽しいでした。

出力：{"suggestions":[{"id":"1","original":"行きます","reason":"「昨日」表示的是过去发生的事情，所以应该使用过去式「行きました」，而不是现在时「行きます」"},{"id":"2","original":"東京へ","reason":"助词「へ」和「に」都可以表示方向，但「に」在口语中更常用于表达明确的到达点，语感更自然"},{"id":"3","original":"良いから","reason":"「から」在书面语中略显生硬，使用「ので」会让语气更委婉、更符合叙述性文章的语感"},{"id":"4","original":"とても楽しいでした","reason":"形容词「楽しい」是い形容词，过去式应该是「楽しかったです」，「楽しいでした」是不正确的活用形式"},{"id":"5","original":"散歩をしました。とても楽しいでした。","reason":"两个短句之间缺乏连接，读起来略显断续，可以合并为「散歩をして、とても楽しかったです」，使文章更流畅自然"}],"overallComment":"本次添削主要涉及时态错误（过去式与现在式的混用）、形容词活用错误，以及部分助词和句子衔接可以更自然。整体意思表达清楚，继续保持！"}"""


def build_user_prompt(original_text: str, target_text: str) -> str:
    """Build the user prompt for text correction."""
    return f"""原文：{original_text}

添削対象：{target_text}"""


def build_messages(original_text: str, target_text: str) -> list[dict]:
    """Build the full message list for chat completion API."""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": FEW_SHOT_EXAMPLE},
        {"role": "user", "content": build_user_prompt(original_text, target_text)},
    ]
