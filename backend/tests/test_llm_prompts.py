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


class TestSemanticReasonQualityInPrompt:
    """harden-semantic-suggestion-reasons: why + accessibility + quotes + SOURCE."""

    def test_system_prompt_requires_why_in_every_reason(self):
        assert "为什么必须" in SYSTEM_PROMPT or "为什么必须改" in SYSTEM_PROMPT
        assert "MUST" in SYSTEM_PROMPT or "必须" in SYSTEM_PROMPT
        assert "指摘" in SYSTEM_PROMPT or "reason" in SYSTEM_PROMPT

    def test_system_prompt_requires_accessible_plain_chinese_why(self):
        assert "通俗" in SYSTEM_PROMPT or "不懂日中翻译" in SYSTEM_PROMPT
        assert "为什么" in SYSTEM_PROMPT

    def test_system_prompt_forbids_japanese_corner_quotes_in_chinese_fields(self):
        assert "禁止" in SYSTEM_PROMPT and "「」" in SYSTEM_PROMPT
        assert '""' in SYSTEM_PROMPT or "双引号" in SYSTEM_PROMPT

    def test_system_prompt_requires_accurate_source_citation(self):
        assert "误引" in SYSTEM_PROMPT or "编造" in SYSTEM_PROMPT
        assert "原文" in SYSTEM_PROMPT

    def test_system_prompt_guides_multi_paragraph_coverage(self):
        assert "多段" in SYSTEM_PROMPT
        assert "覆盖" in SYSTEM_PROMPT

    def test_system_prompt_forbids_location_only_que_shao(self):
        assert "缺少" in SYSTEM_PROMPT
        assert "不合格" in SYSTEM_PROMPT

    def test_system_prompt_forbids_inventing_false_particles(self):
        assert "臆造" in SYSTEM_PROMPT or "编造" in SYSTEM_PROMPT
        assert "助词" in SYSTEM_PROMPT

    def test_user_prompt_reinforces_why_quotes_and_coverage(self):
        prompt = build_user_prompt("原文", "対象")
        assert "为什么必须改" in prompt
        assert "缺少" in prompt
        assert "「」" in prompt  # forbid mention
        assert "多段" in prompt or "覆盖" in prompt

    def test_few_shot_reasons_include_necessity_cues(self):
        # Compliant few-shot should not be location-only 缺少 patterns.
        assert "因此" in FEW_SHOT_EXAMPLE or "必须" in FEW_SHOT_EXAMPLE
        assert "才能" in FEW_SHOT_EXAMPLE or "需要" in FEW_SHOT_EXAMPLE

    def test_few_shot_uses_chinese_double_quotes_not_corner_brackets(self):
        assert "“" in FEW_SHOT_EXAMPLE or '"' in FEW_SHOT_EXAMPLE
        # Reasons in the JSON output example must not teach 「」 cites.
        # (Prompt meta text may still use 「原文」 labels — check reason bodies.)
        assert '"reason":"“' in FEW_SHOT_EXAMPLE or '"reason":"' in FEW_SHOT_EXAMPLE
        assert "「昨日」" not in FEW_SHOT_EXAMPLE
