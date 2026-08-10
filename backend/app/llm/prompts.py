"""
Prompts for AI text correction suggestions.
Ported from frontend/src/lib/webllm/prompts/ for consistency.
"""

SYSTEM_PROMPT = """翻译校对。只输出JSON，禁止其他文字。禁止```。禁止尾随逗号。

格式：{"指摘":[{"番号":1,"箇所":"片段","コメント":"建议"}],"全体講評":"总评"}
最多5条指摘。"""

FEW_SHOT_EXAMPLE = """例：原文「答えようがありませんでした」译文「我并不想回复」
输出：{"指摘":[{"番号":1,"箇所":"我并不想回复","コメント":"ようがない是无法，非不想"}],"全体講評":"OK"}"""


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
