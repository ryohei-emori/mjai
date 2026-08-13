"""
Tests for backend/app/llm/prompts.py framing and language rules.
"""

from app.llm.prompts import (
    CORRECTION_TASK_BRIEF,
    SYSTEM_PROMPT,
    FEW_SHOT_EXAMPLE,
    build_user_prompt,
    build_messages,
)


class TestCorrectionTaskBrief:
    def test_brief_constant_matches_product_wording(self):
        assert CORRECTION_TASK_BRIEF == (
            "意味の不一致、文法、流暢さ、スペルミスに焦点を当てて、この課題を添削してください。"
        )

    def test_system_prompt_leads_with_brief(self):
        assert SYSTEM_PROMPT.startswith(CORRECTION_TASK_BRIEF)

    def test_user_prompt_includes_brief(self):
        prompt = build_user_prompt("原文A", "対象B")
        assert prompt.startswith(CORRECTION_TASK_BRIEF)
        assert "原文A" in prompt
        assert "対象B" in prompt


class TestLanguageRulesInPrompt:
    def test_system_prompt_requires_simplified_chinese_for_explanations(self):
        assert "简体中文" in SYSTEM_PROMPT or "簡体字中国語" in SYSTEM_PROMPT
        assert "reason" in SYSTEM_PROMPT
        assert "overallComment" in SYSTEM_PROMPT
        assert (
            "ひらがな" in SYSTEM_PROMPT
            or "カタカナ" in SYSTEM_PROMPT
            or "假名" in SYSTEM_PROMPT
        )

    def test_system_prompt_keeps_original_and_source_excerpt_japanese(self):
        assert "original" in SYSTEM_PROMPT
        assert "sourceExcerpt" in SYSTEM_PROMPT
        # original must stay TARGET-language (Japanese); prompt may say 日语/日本語
        assert "日语" in SYSTEM_PROMPT or "日本語" in SYSTEM_PROMPT

    def test_few_shot_uses_chinese_reasons(self):
        assert "应该使用过去式" in FEW_SHOT_EXAMPLE or "过去" in FEW_SHOT_EXAMPLE
        assert "本次添削" in FEW_SHOT_EXAMPLE or "整体" in FEW_SHOT_EXAMPLE

    def test_build_messages_order(self):
        messages = build_messages("o", "t")
        assert messages[0]["role"] == "system"
        assert CORRECTION_TASK_BRIEF in messages[0]["content"]
        assert messages[-1]["role"] == "user"
        assert CORRECTION_TASK_BRIEF in messages[-1]["content"]
