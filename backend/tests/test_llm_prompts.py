"""
Tests for backend/app/llm/prompts.py framing and language rules.
"""

from app.llm.prompts import (
    CORRECTION_TASK_BRIEF,
    EXEMPLAR_REFERENCE_RULES,
    OUTPUT_CONTRACT,
    SYSTEM_PROMPT,
    SYSTEM_PROMPT_BODY,
    FEW_SHOT_EXAMPLE,
    build_system_prompt,
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
        assert "规范" in FEW_SHOT_EXAMPLE or "语域" in FEW_SHOT_EXAMPLE
        assert "优点" in FEW_SHOT_EXAMPLE or "已能传达" in FEW_SHOT_EXAMPLE or "核心" in FEW_SHOT_EXAMPLE

    def test_build_messages_order(self):
        messages = build_messages("o", "t")
        assert messages[0]["role"] == "system"
        assert CORRECTION_TASK_BRIEF in messages[0]["content"]
        assert messages[-1]["role"] == "user"
        assert CORRECTION_TASK_BRIEF in messages[-1]["content"]


class TestSemanticReasonQualityInPrompt:
    """harden-semantic-suggestion-reasons + gemini quality bar."""

    def test_system_prompt_requires_why_in_every_reason(self):
        assert "为什么必须" in SYSTEM_PROMPT or "为什么必须改" in SYSTEM_PROMPT
        assert "MUST" in SYSTEM_PROMPT or "必须" in SYSTEM_PROMPT
        assert "指摘" in SYSTEM_PROMPT or "reason" in SYSTEM_PROMPT

    def test_system_prompt_requires_accessible_plain_chinese_why(self):
        assert "通俗" in SYSTEM_PROMPT or "不懂日中翻译" in SYSTEM_PROMPT
        assert "为什么" in SYSTEM_PROMPT

    def test_system_prompt_quote_policy_jp_cites_vs_chinese_meta(self):
        # 「」 allowed for JP TARGET cites; Chinese meta uses "" / “”;
        # forbid 「」 wrapping Chinese explanation words.
        assert "「」" in SYSTEM_PROMPT
        assert '""' in SYSTEM_PROMPT or "双引号" in SYSTEM_PROMPT
        assert "时态" in SYSTEM_PROMPT or "中文说明" in SYSTEM_PROMPT

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

    def test_system_prompt_overall_comment_strengths_then_gaps(self):
        assert "优点" in SYSTEM_PROMPT
        assert "先" in SYSTEM_PROMPT

    def test_system_prompt_reason_shape_problem_fix_why_natural_prose(self):
        # Natural Chinese problem→fix→why; forbid spoken 现状：/推荐： labels.
        assert "为什么必须" in SYSTEM_PROMPT or "为什么必须改" in SYSTEM_PROMPT
        assert "推荐" in SYSTEM_PROMPT or "改法" in SYSTEM_PROMPT
        assert "自然" in SYSTEM_PROMPT
        assert "现状：" in SYSTEM_PROMPT or "現状：" in SYSTEM_PROMPT
        assert "禁止" in SYSTEM_PROMPT
        assert "冒号" in SYSTEM_PROMPT or "标签" in SYSTEM_PROMPT

    def test_system_prompt_coverage_density_not_stop_early(self):
        assert "至少 5" in SYSTEM_PROMPT or "至少5" in SYSTEM_PROMPT
        assert "逐段" in SYSTEM_PROMPT or "多段" in SYSTEM_PROMPT
        assert "1–2" in SYSTEM_PROMPT or "1-2" in SYSTEM_PROMPT or "一两" in SYSTEM_PROMPT

    def test_system_prompt_cn_jp_literary_academic_domain(self):
        assert "中译日" in SYSTEM_PROMPT or "文学" in SYSTEM_PROMPT
        assert "规范译词" in SYSTEM_PROMPT or "语域" in SYSTEM_PROMPT

    def test_user_prompt_reinforces_why_quotes_and_coverage(self):
        prompt = build_user_prompt("原文", "対象")
        assert "为什么必须改" in prompt
        assert "缺少" in prompt
        assert "「」" in prompt
        assert "优点" in prompt or "先写优点" in prompt
        assert "多段" in prompt or "覆盖" in prompt

    def test_few_shot_reasons_include_necessity_cues(self):
        assert "规范" in FEW_SHOT_EXAMPLE or "语域" in FEW_SHOT_EXAMPLE
        assert "宜改为" in FEW_SHOT_EXAMPLE or "→" in FEW_SHOT_EXAMPLE
        # Reasons themselves must not use spoken label prefixes (intro may
        # mention the forbidden labels as anti-patterns).
        assert '"reason":"现状：' not in FEW_SHOT_EXAMPLE
        assert '"reason":"推荐：' not in FEW_SHOT_EXAMPLE
        assert '"reason":"現状：' not in FEW_SHOT_EXAMPLE

    def test_few_shot_gemini_shaped_quotes_and_overall(self):
        assert "“史诗”" in FEW_SHOT_EXAMPLE or "“" in FEW_SHOT_EXAMPLE
        assert "「叙事詩」" in FEW_SHOT_EXAMPLE
        assert "已能传达" in FEW_SHOT_EXAMPLE or "优点" in FEW_SHOT_EXAMPLE


class TestTeachingQualityInPrompt:
    """improve-suggestion-teaching-quality — competence teaching bar."""

    def test_system_prompt_prioritizes_essential_competence_gaps(self):
        assert "实质问题" in SYSTEM_PROMPT or "能力" in SYSTEM_PROMPT
        assert "意义偏移" in SYSTEM_PROMPT or "情态" in SYSTEM_PROMPT

    def test_system_prompt_forbids_trivial_surface_as_main_critique(self):
        assert "表面" in SYSTEM_PROMPT
        assert "省略" in SYSTEM_PROMPT or "简化" in SYSTEM_PROMPT

    def test_system_prompt_forbids_bare_source_token_swap(self):
        assert "跟原文对词" in SYSTEM_PROMPT or "原文用了" in SYSTEM_PROMPT
        assert "添削" in SYSTEM_PROMPT

    def test_system_prompt_requires_contrastive_nuance_for_lexical_upgrades(self):
        assert "对比" in SYSTEM_PROMPT
        assert "语感" in SYSTEM_PROMPT or "语义" in SYSTEM_PROMPT

    def test_system_prompt_class_of_error_for_future_translations(self):
        assert "今后" in SYSTEM_PROMPT
        assert "翻译" in SYSTEM_PROMPT or "译文" in SYSTEM_PROMPT

    def test_user_prompt_reinforces_teaching_bar(self):
        prompt = build_user_prompt("原文", "対象")
        assert "表面" in prompt or "对词" in prompt
        assert "对比" in prompt
        assert "今后" in prompt

    def test_few_shot_shows_contrastive_nuance_not_anti_patterns(self):
        assert "偏" in FEW_SHOT_EXAMPLE  # contrastive 偏口语 / 偏书面
        assert "「しかし」" in FEW_SHOT_EXAMPLE
        # Must not model the three anti-patterns as good output.
        assert "可以省略" not in FEW_SHOT_EXAMPLE
        assert "套语" not in FEW_SHOT_EXAMPLE
        assert "更能体现" not in FEW_SHOT_EXAMPLE

    def test_teaching_quality_fixtures_document_bad_and_good(self):
        from tests.fixtures.teaching_quality_cases import (
            TEACHING_BAD_PREFERENCE_NO_CONTRAST,
            TEACHING_BAD_SOURCE_TOKEN_SWAP,
            TEACHING_BAD_TRIVIAL_SURFACE,
            TEACHING_GOOD_CONTRASTIVE_REASON,
            TEACHING_GOOD_CLASS_OF_ERROR_REASON,
        )

        assert "省略" in TEACHING_BAD_TRIVIAL_SURFACE or "紙に" in TEACHING_BAD_TRIVIAL_SURFACE
        assert "原文" in TEACHING_BAD_SOURCE_TOKEN_SWAP
        assert "更能体现" in TEACHING_BAD_PREFERENCE_NO_CONTRAST
        assert "偏" in TEACHING_GOOD_CONTRASTIVE_REASON
        assert "今后" in TEACHING_GOOD_CLASS_OF_ERROR_REASON or "后续" in TEACHING_GOOD_CLASS_OF_ERROR_REASON


class TestFewShotExemplarCoherence:
    """refine-prompt-instruction-coherence — the example must demonstrate the bar."""

    @staticmethod
    def _few_shot_suggestions():
        from app.llm.parser import parse_model_output

        return parse_model_output(FEW_SHOT_EXAMPLE)["suggestions"]

    def test_few_shot_demonstrates_density_target(self):
        # Demonstrated cardinality anchors the model harder than the numeric
        # target does, so the example must not show fewer items than it asks for.
        assert len(self._few_shot_suggestions()) >= 5

    def test_few_shot_states_count_is_not_a_cap(self):
        assert "不是上限" in FEW_SHOT_EXAMPLE

    def test_few_shot_items_are_distinct(self):
        originals = [s["original"] for s in self._few_shot_suggestions()]
        assert len(originals) == len(set(originals))

    def test_few_shot_demonstrates_omitted_source_excerpt(self):
        excerpts = [s["sourceExcerpt"] for s in self._few_shot_suggestions()]
        assert any(not e for e in excerpts), "no item omits sourceExcerpt"
        assert any(e for e in excerpts), "no item demonstrates a present sourceExcerpt"

    def test_few_shot_covers_grammar_and_modality_categories(self):
        reasons = " ".join(s["reason"] for s in self._few_shot_suggestions())
        assert "主语" in reasons or "谓语" in reasons or "骨架" in reasons
        assert "推测" in reasons or "推量" in reasons or "断定" in reasons

    def test_few_shot_reasons_carry_no_model_facing_directives(self):
        # Anti-pattern rules belong in the prompt, not inside exemplar output
        # a learner reads.
        for suggestion in self._few_shot_suggestions():
            assert "不要主推" not in suggestion["reason"]
            assert "当作主指摘" not in suggestion["reason"]

    def test_system_prompt_has_no_count_trading_hedge(self):
        assert "质量优先于条数" not in SYSTEM_PROMPT
        assert "不等于可以少报" in SYSTEM_PROMPT

    def test_system_prompt_bounds_length_per_item_not_globally(self):
        assert "宜简明完整" not in SYSTEM_PROMPT
        assert "2–4 句" in SYSTEM_PROMPT or "2-4 句" in SYSTEM_PROMPT

    def test_system_prompt_forbids_meta_instructions_in_reason(self):
        assert "元指令" in SYSTEM_PROMPT

    def test_system_prompt_explains_when_source_excerpt_is_omitted(self):
        assert "没有对应片段" in SYSTEM_PROMPT

    def test_few_shot_no_longer_restates_anti_label_rule(self):
        # The rule stays in SYSTEM_PROMPT and the user reminder; the example
        # demonstrates compliance instead of repeating the prohibition.
        assert "现状：" not in FEW_SHOT_EXAMPLE
        assert "现状：" in SYSTEM_PROMPT
        assert "现状：" in build_user_prompt("原文", "対象")


class TestOptionalExemplarTranslation:
    """add-optional-exemplar-translation-input — reference-only calibration."""

    BASELINE_USER_PROMPT = build_user_prompt("原文A", "対象B")

    def test_absent_exemplar_leaves_prompt_byte_identical(self):
        # The whole backward-compat guarantee: users without an exemplar must
        # get exactly today's prompt, not a prompt with an empty section.
        for empty in (None, "", "   ", "\n\t "):
            assert build_user_prompt("原文A", "対象B", empty) == self.BASELINE_USER_PROMPT
            assert build_system_prompt(empty) == SYSTEM_PROMPT

    def test_absent_exemplar_omits_exemplar_label(self):
        assert "模範回答訳文" not in self.BASELINE_USER_PROMPT

    def test_non_empty_exemplar_appears_between_source_and_target(self):
        prompt = build_user_prompt("原文A", "対象B", "模範の訳文C")
        assert "模範の訳文C" in prompt
        assert "模範回答訳文" in prompt
        assert prompt.index("原文A") < prompt.index("模範の訳文C") < prompt.index("対象B")

    def test_exemplar_is_stripped_before_insertion(self):
        prompt = build_user_prompt("原文A", "対象B", "  模範の訳文C \n")
        assert "模範回答訳文（参考・校准用，禁止直接当作理由或原样照搬）：模範の訳文C" in prompt

    def test_exemplar_rules_appended_to_system_prompt_only_when_present(self):
        # Exemplar rules land between the rules body and the output contract,
        # so the JSON schema stays the last thing the model reads.
        with_exemplar = build_system_prompt("模範の訳文C")
        assert with_exemplar.startswith(SYSTEM_PROMPT_BODY)
        assert EXEMPLAR_REFERENCE_RULES.strip() in with_exemplar
        assert with_exemplar.endswith(OUTPUT_CONTRACT)
        assert EXEMPLAR_REFERENCE_RULES.strip() not in SYSTEM_PROMPT

    def test_exemplar_rules_forbid_copying_and_citing_the_exemplar(self):
        # Live A/B probe showed an unguarded exemplar cuts issue coverage; these
        # are the clauses that keep the critique grounded in 原文.
        assert "以原文为判断依据" in EXEMPLAR_REFERENCE_RULES
        assert "与参考译文不同" in EXEMPLAR_REFERENCE_RULES
        assert "禁止在 reason" in EXEMPLAR_REFERENCE_RULES
        assert "不是合格的理由" in EXEMPLAR_REFERENCE_RULES or "永远不是" in EXEMPLAR_REFERENCE_RULES

    def test_build_messages_threads_exemplar_into_both_roles(self):
        messages = build_messages("o", "t", "模範の訳文C")
        assert messages[0]["role"] == "system"
        assert "模範回答訳文" in messages[0]["content"]
        assert "模範の訳文C" in messages[-1]["content"]

    def test_build_messages_without_exemplar_matches_two_arg_form(self):
        assert build_messages("o", "t", None) == build_messages("o", "t")
        assert build_messages("o", "t", "") == build_messages("o", "t")


class TestNoDownstreamSuggestionCap:
    """Prompt-level density must be the only thing governing item count."""

    def test_parser_returns_every_suggestion(self):
        import json

        from app.llm.parser import parse_model_output

        payload = {
            "suggestions": [
                {"id": str(i), "original": f"語{i}", "reason": f"这里有问题{i}，应改为别的写法，因为会影响理解"}
                for i in range(1, 13)
            ],
            "overallComment": "先说优点，再说问题。",
        }
        result = parse_model_output(json.dumps(payload, ensure_ascii=False))
        assert len(result["suggestions"]) == 12


class TestEditablePromptComposition:
    """editable-prompt-model-log-and-critique-fix — body vs code-owned contract."""

    def test_default_prompt_is_body_plus_contract(self):
        assert SYSTEM_PROMPT == f"{SYSTEM_PROMPT_BODY}\n{OUTPUT_CONTRACT}"

    def test_contract_carries_the_json_only_rule_and_schema(self):
        assert "只输出 JSON" in OUTPUT_CONTRACT
        assert "格式：" in OUTPUT_CONTRACT
        assert '"suggestions"' in OUTPUT_CONTRACT
        assert '"overallComment"' in OUTPUT_CONTRACT
        # The editable half must not carry the machine contract with it.
        assert "格式：" not in SYSTEM_PROMPT_BODY

    def test_override_replaces_only_the_body(self):
        composed = build_system_prompt(None, "自定义规则正文")
        assert composed == f"自定义规则正文\n{OUTPUT_CONTRACT}"
        assert SYSTEM_PROMPT_BODY not in composed

    def test_override_that_never_mentions_json_still_gets_the_contract(self):
        composed = build_system_prompt(None, "随便写点什么。")
        assert "只输出 JSON" in composed
        assert composed.endswith(OUTPUT_CONTRACT)

    def test_blank_override_falls_back_to_the_default_prompt(self):
        for blank in (None, "", "   ", "\n\t "):
            assert build_system_prompt(None, blank) == SYSTEM_PROMPT

    def test_override_is_trimmed_before_composition(self):
        assert build_system_prompt(None, "  规则  ") == f"规则\n{OUTPUT_CONTRACT}"

    def test_build_messages_threads_the_override_into_the_system_message(self):
        messages = build_messages("原文", "対象", None, "自定义规则正文")
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == f"自定义规则正文\n{OUTPUT_CONTRACT}"
        # Only the system message changes; the few-shot and user turns do not.
        assert messages[1:] == build_messages("原文", "対象")[1:]

    def test_build_messages_without_override_matches_the_three_arg_form(self):
        assert build_messages("o", "t", None, None) == build_messages("o", "t")


class TestTargetLanguageCritiqueRules:
    """The rules a reported session showed the previous prompt not enforcing."""

    def test_recommended_forms_must_be_japanese(self):
        assert "推荐形必须是日语" in SYSTEM_PROMPT
        assert "理论上" in SYSTEM_PROMPT  # the reported Chinese-recommendation case
        assert "推荐形" in build_user_prompt("原文", "対象")

    def test_only_the_target_text_may_be_corrected(self):
        assert "原文是判断依据，不是添削对象" in SYSTEM_PROMPT
        assert "禁止改写原文" in build_user_prompt("原文", "対象")

    def test_interchangeable_synonyms_are_not_faults(self):
        assert "近义互换不是错误" in SYSTEM_PROMPT
        assert "比較⇄対比" in SYSTEM_PROMPT
        assert "研究者⇄学者" in SYSTEM_PROMPT
        assert "近义替换" in build_user_prompt("原文", "対象")

    def test_wording_items_must_name_a_defect_category(self):
        assert "更准确/更自然/更正式/更简洁" in SYSTEM_PROMPT

    def test_recommended_form_must_be_substituted_and_checked(self):
        assert "代入原句" in SYSTEM_PROMPT
        assert "睡眠が需要だ" in SYSTEM_PROMPT  # the reported broken recommendation

    def test_explanations_must_frame_meaning_transfer_not_word_mapping(self):
        assert "日语读者会读成什么" in SYSTEM_PROMPT
        assert "不是逐词替换" in SYSTEM_PROMPT

    def test_digit_and_notation_faults_are_a_named_category(self):
        assert "９点５時間" in SYSTEM_PROMPT
        assert "9.5時間" in SYSTEM_PROMPT


class TestFewShotObeysTargetLanguageRules:
    @staticmethod
    def _suggestions():
        from app.llm.parser import parse_model_output

        return parse_model_output(FEW_SHOT_EXAMPLE)["suggestions"]

    def test_no_recommended_form_is_chinese(self):
        from app.llm.parser import has_non_japanese_recommendation, parse_model_output

        assert has_non_japanese_recommendation(parse_model_output(FEW_SHOT_EXAMPLE)) is False

    def test_every_item_states_a_reader_facing_consequence(self):
        reasons = self._suggestions()
        consequence_cues = ("读者", "读成", "读不通", "读到", "误")
        for suggestion in reasons:
            assert any(cue in suggestion["reason"] for cue in consequence_cues), (
                f"item {suggestion['id']} explains no reader-facing consequence"
            )

    def test_demonstrates_the_notation_category(self):
        reasons = " ".join(s["reason"] for s in self._suggestions())
        assert "9.5時間" in reasons

    def test_intro_states_recommendations_are_japanese_and_not_synonym_swaps(self):
        assert "推荐形都用日语给出" in FEW_SHOT_EXAMPLE
        assert "近义替换" in FEW_SHOT_EXAMPLE
