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
output on smaller models. Kept in Japanese/English to match the task's input and
expected output language.
"""

SYSTEM_PROMPT = """あなたは日本語の文章添削アシスタントです。「原文」と「添削対象」を比較し、誤りや改善点を指摘してください。

出力はJSONのみ。それ以外の文章、説明、Markdownのコードブロック（```）は一切出力しないこと。JSON内で末尾カンマを使わないこと。

出力形式：
{"suggestions":[{"id":"1","original":"該当箇所の抜粋","reason":"指摘理由と修正案"}],"overallComment":"全体講評"}

suggestionsは最大3件まで。問題が3件より多く見つかった場合は、最も重要な指摘を優先すること。問題が3件未満しか見つからない場合は、無理に3件に合わせず、実際に見つかった件数のみを返すこと（架空の指摘を作らないこと）。"original"と"reason"は添削対象と同じ言語（日本語）で記述すること。"""

FEW_SHOT_EXAMPLE = """例：
原文：彼は昨日、東京に行きました
添削対象：彼は昨日、東京へ行きます

出力：{"suggestions":[{"id":"1","original":"行きます","reason":"「昨日」は過去の出来事なので、過去形の「行きました」が適切です"}],"overallComment":"時制の誤りが1件あります"}"""


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
