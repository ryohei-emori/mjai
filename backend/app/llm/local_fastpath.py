"""Conservative, sub-millisecond fixes for unambiguous Japanese typos."""

from __future__ import annotations

from typing import Any


_TYPO_RULES: tuple[tuple[str, str, str], ...] = (
    ("でしだ", "でした", "「でしだ」は「でした」の誤記です。"),
    ("ましだ", "ました", "「ましだ」は「ました」の誤記です。"),
    ("くださぃ", "ください", "「くださぃ」は「ください」の誤記です。"),
    ("ござぃます", "ございます", "「ござぃます」は「ございます」の誤記です。"),
)


def try_local_fastpath(original_text: str, target_text: str) -> dict[str, Any] | None:
    """Return a schema-compatible result only for a very safe typo pattern."""
    if not target_text or len(target_text) > 160 or len(original_text) > 160:
        return None

    matches = [(wrong, right, reason) for wrong, right, reason in _TYPO_RULES if wrong in target_text]
    if len(matches) != 1:
        return None
    wrong, right, reason = matches[0]
    corrected = target_text.replace(wrong, right, 1)
    return {
        "suggestions": [
            {
                "id": "local-1",
                "original": wrong,
                "reason": (
                    f"{reason}改为「{right}」后，日语的活用和拼写都成立。"
                    "这是明确的字形错误，不涉及语义判断。"
                ),
                "sourceExcerpt": original_text,
            }
        ],
        "overallComment": (
            "短文的基本内容已经可以理解。"
            f"把明确的误记「{wrong}」改为「{right}」后，即可保留原句意思。"
        ),
        "llmProvider": "local-fastpath",
        "llmModel": "deterministic-japanese-typo-v1",
        "fastPathCorrectedText": corrected,
    }
