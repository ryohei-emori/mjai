"""
Prompts for AI text correction suggestions.

Uses English keys as canonical schema (per AGENTS.md Response Schema section):
- suggestions: array of {id, original, reason}
- overallComment: string

Parser has dual-key fallback for backward compat with older WebLLM Japanese-key format.
"""

SYSTEM_PROMPT = """翻译校对。只输出JSON，禁止其他文字。禁止```。禁止尾随逗号。

格式：{"suggestions":[{"id":"1","original":"片段","reason":"建议"}],"overallComment":"总评"}
最多5条suggestions。"""

FEW_SHOT_EXAMPLE = """例：原文「答えようがありませんでした」译文「我并不想回复」
输出：{"suggestions":[{"id":"1","original":"我并不想回复","reason":"ようがない是无法，非不想"}],"overallComment":"OK"}"""


def build_user_prompt(original_text: str, target_text: str) -> str:
    """Build the user prompt for text correction."""
    return f"""原文：{original_text}

译文：{target_text}"""


def build_messages(original_text: str, target_text: str) -> list[dict]:
    """Build the full message list for chat completion API."""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": FEW_SHOT_EXAMPLE},
        {"role": "user", "content": build_user_prompt(original_text, target_text)},
    ]
