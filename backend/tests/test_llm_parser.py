"""
Tests for backend/app/llm/parser.py
"""

import json

import pytest
from app.llm.parser import (
    parse_model_output,
    remove_trailing_commas,
    strip_markdown_fences,
    repair_truncated_json,
    extract_json,
    safe_json_parse,
    has_non_chinese_reason,
    has_weak_critique_reason,
    has_japanese_corner_quotes_in_critique,
)
from tests.fixtures.semantic_reason_cases import (
    CASE_A_BAD_REASON,
    CASE_A_BAD_REASON_LEGACY_CORNER,
    CASE_A_NOTES,
    CASE_A_TARGET_TEXT,
    CASE_B_COMPLIANT_REASON,
    CASE_B_TARGET_TEXT,
    CASE_B_WEAK_REASON,
    CASE_B_WEAK_REASON_LEGACY_CORNER,
    CASE_C_BAD_REASON,
    CASE_C_NOTES,
    CASE_C_TARGET_TEXT,
    CASE_CORNER_QUOTE_IN_CHINESE_REASON,
    CASE_DOUBLE_QUOTE_COMPLIANT_REASON,
)


class TestRemoveTrailingCommas:
    def test_removes_array_trailing_comma(self):
        assert remove_trailing_commas('[1, 2, 3,]') == '[1, 2, 3]'
    
    def test_removes_object_trailing_comma(self):
        assert remove_trailing_commas('{"a": 1, "b": 2,}') == '{"a": 1, "b": 2}'
    
    def test_handles_whitespace(self):
        assert remove_trailing_commas('[1, 2,  ]') == '[1, 2]'
        assert remove_trailing_commas('{"a": 1,  }') == '{"a": 1}'
    
    def test_no_trailing_comma(self):
        assert remove_trailing_commas('[1, 2, 3]') == '[1, 2, 3]'


class TestStripMarkdownFences:
    def test_strips_json_fence(self):
        text = '```json\n{"key": "value"}\n```'
        result = strip_markdown_fences(text)
        assert '{"key": "value"}' in result
        assert '```' not in result
    
    def test_strips_plain_fence(self):
        text = '```\n{"key": "value"}\n```'
        result = strip_markdown_fences(text)
        assert '{"key": "value"}' in result
        assert '```' not in result
    
    def test_case_insensitive(self):
        text = '```JSON\n{"key": "value"}\n```'
        result = strip_markdown_fences(text)
        assert '{"key": "value"}' in result
        assert '```' not in result


class TestRepairTruncatedJson:
    def test_closes_missing_bracket(self):
        result = repair_truncated_json('{"arr": [1, 2, 3')
        assert result.count(']') >= 1
        assert result.count('}') >= 1
    
    def test_removes_trailing_comma(self):
        result = repair_truncated_json('{"a": 1,')
        assert not result.endswith(',')

    def test_closes_nested_structure_in_correct_order(self):
        """Regression: closing punctuation must be LIFO (}]}), not grouped
        by bracket type (]}}), or the repaired string fails to parse."""
        result = repair_truncated_json('{"suggestions":[{"id":"1","original":"a","reason":"b"')
        assert json.loads(result) == {"suggestions": [{"id": "1", "original": "a", "reason": "b"}]}

    def test_closes_dangling_string_mid_truncation(self):
        result = repair_truncated_json('{"suggestions":[{"id":"1","original":"a","reason":"unfinished')
        parsed = json.loads(result)
        assert parsed["suggestions"][0]["reason"] == ""


class TestExtractJson:
    def test_extracts_shiteki_json(self):
        text = 'Some preamble {"指摘": []} and postamble'
        result = extract_json(text)
        assert result is not None
        assert '"指摘"' in result
    
    def test_extracts_first_last_brace(self):
        text = 'Preamble {"key": "value"} postamble'
        result = extract_json(text)
        assert result == '{"key": "value"}'
    
    def test_returns_none_for_no_json(self):
        text = 'No JSON here'
        assert extract_json(text) is None

    def test_truncated_response_keeps_earlier_complete_items(self):
        """Regression: naive rfind('}') matched the first item's closing
        brace and silently discarded the second (truncated) item's data."""
        text = '{"suggestions":[{"id":"1","original":"a","reason":"b"},{"id":"2","original":"c","reason":"d"'
        result = extract_json(text)
        assert '"id":"2"' in result

    def test_stops_at_matching_brace_ignoring_postamble_braces(self):
        text = '{"key": "value"} and here is a stray } in the postamble'
        result = extract_json(text)
        assert result == '{"key": "value"}'


class TestSafeJsonParse:
    def test_parses_valid_json(self):
        result = safe_json_parse('{"key": "value"}')
        assert result == {"key": "value"}
    
    def test_handles_trailing_comma(self):
        result = safe_json_parse('{"key": "value",}')
        assert result == {"key": "value"}
    
    def test_handles_markdown_fences(self):
        result = safe_json_parse('```json\n{"key": "value"}\n```')
        assert result == {"key": "value"}
    
    def test_returns_none_for_invalid(self):
        result = safe_json_parse('not json at all')
        assert result is None


class TestParseModelOutput:
    def test_parses_valid_response(self):
        text = '''{"指摘": [{"番号": 1, "箇所": "テスト", "コメント": "修正してください"}], "全体講評": "全体的に良い"}'''
        result = parse_model_output(text)
        
        assert len(result["suggestions"]) == 1
        assert result["suggestions"][0]["id"] == "1"
        assert result["suggestions"][0]["original"] == "テスト"
        assert result["suggestions"][0]["reason"] == "修正してください"
        assert result["overallComment"] == "全体的に良い"
    
    def test_parses_multiple_suggestions(self):
        text = '''{"指摘": [
            {"番号": 1, "箇所": "箇所1", "コメント": "コメント1"},
            {"番号": 2, "箇所": "箇所2", "コメント": "コメント2"}
        ], "全体講評": "総評"}'''
        result = parse_model_output(text)
        
        assert len(result["suggestions"]) == 2
        assert result["suggestions"][0]["original"] == "箇所1"
        assert result["suggestions"][1]["original"] == "箇所2"
    
    def test_handles_markdown_wrapped(self):
        text = '''```json
{"指摘": [{"番号": 1, "箇所": "テスト", "コメント": "OK"}], "全体講評": "良い"}
```'''
        result = parse_model_output(text)
        
        assert len(result["suggestions"]) == 1
        assert result["overallComment"] == "良い"
    
    def test_handles_trailing_commas(self):
        text = '''{"指摘": [{"番号": 1, "箇所": "テスト", "コメント": "OK",},], "全体講評": "良い",}'''
        result = parse_model_output(text)
        
        assert len(result["suggestions"]) == 1
    
    def test_handles_preamble_postamble(self):
        text = '''Here is the JSON:
{"指摘": [{"番号": 1, "箇所": "箇所", "コメント": "コメント"}], "全体講評": "OK"}
That's the response.'''
        result = parse_model_output(text)
        
        assert len(result["suggestions"]) == 1
    
    def test_returns_empty_on_invalid(self):
        result = parse_model_output("This is not JSON at all")
        
        assert result["suggestions"] == []
        assert "抽出できませんでした" in result["overallComment"]
    
    def test_handles_empty_suggestions_array(self):
        text = '''{"指摘": [], "全体講評": "問題ありません"}'''
        result = parse_model_output(text)
        
        assert result["suggestions"] == []
        assert result["overallComment"] == "問題ありません"
    
    def test_handles_missing_fields(self):
        """An item with no original/reason content at all is now filtered
        out as a fully-blank item (2026-08 refine-suggestion-card-interactions),
        rather than surfaced as an empty suggestion — see
        TestParseModelOutput's blank-item-filtering tests below."""
        text = '''{"指摘": [{"番号": 1}], "全体講評": ""}'''
        result = parse_model_output(text)
        
        assert result["suggestions"] == []
    
    # === Tests for English key format (Groq/Cloudflare may output this) ===
    
    def test_parses_english_keys(self):
        """Test that parser handles English key format from some LLMs."""
        text = '''{"suggestions": [{"id": "1", "original": "テスト箇所", "reason": "修正理由"}], "overallComment": "全体的に良い"}'''
        result = parse_model_output(text)
        
        assert len(result["suggestions"]) == 1
        assert result["suggestions"][0]["id"] == "1"
        assert result["suggestions"][0]["original"] == "テスト箇所"
        assert result["suggestions"][0]["reason"] == "修正理由"
        assert result["overallComment"] == "全体的に良い"
    
    def test_parses_english_keys_multiple(self):
        """Test English format with multiple suggestions."""
        text = '''{"suggestions": [
            {"id": "1", "original": "箇所1", "reason": "理由1"},
            {"id": "2", "original": "箇所2", "reason": "理由2"}
        ], "overallComment": "総評コメント"}'''
        result = parse_model_output(text)
        
        assert len(result["suggestions"]) == 2
        assert result["suggestions"][0]["original"] == "箇所1"
        assert result["suggestions"][1]["original"] == "箇所2"
        assert result["overallComment"] == "総評コメント"
    
    def test_english_keys_with_markdown_fence(self):
        """Test English format wrapped in markdown code fence."""
        text = '''```json
{"suggestions": [{"id": "1", "original": "test", "reason": "fix it"}], "overallComment": "ok"}
```'''
        result = parse_model_output(text)
        
        assert len(result["suggestions"]) == 1
        assert result["suggestions"][0]["original"] == "test"
        assert result["overallComment"] == "ok"
    
    def test_english_keys_empty_suggestions(self):
        """Test English format with empty suggestions array."""
        text = '''{"suggestions": [], "overallComment": "No issues found"}'''
        result = parse_model_output(text)
        
        assert result["suggestions"] == []
        assert result["overallComment"] == "No issues found"
    
    def test_mixed_keys_prefers_japanese(self):
        """Test that Japanese keys take precedence when both present."""
        text = '''{"指摘": [{"箇所": "日本語", "コメント": "日本語コメント"}], "全体講評": "日本語総評", "suggestions": [], "overallComment": "English"}'''
        result = parse_model_output(text)
        
        assert len(result["suggestions"]) == 1
        assert result["suggestions"][0]["original"] == "日本語"
        assert result["overallComment"] == "日本語総評"
    
    def test_english_keys_with_preamble(self):
        """Test English format with preamble text."""
        text = '''Here is the analysis:
{"suggestions": [{"id": "1", "original": "error", "reason": "should be fixed"}], "overallComment": "Good overall"}
Hope this helps!'''
        result = parse_model_output(text)
        
        assert len(result["suggestions"]) == 1
        assert result["suggestions"][0]["original"] == "error"
    
    # === Tests for alternative field name fallbacks ===
    
    def test_text_comment_keys(self):
        """Test that parser handles text/comment as alternative field names."""
        text = '''{"suggestions": [{"id": "1", "text": "問題箇所", "comment": "修正理由"}], "overallComment": "OK"}'''
        result = parse_model_output(text)
        
        assert len(result["suggestions"]) == 1
        assert result["suggestions"][0]["original"] == "問題箇所"
        assert result["suggestions"][0]["reason"] == "修正理由"
    
    def test_content_suggestion_keys(self):
        """Test that parser handles content/suggestion as alternative field names."""
        text = '''{"suggestions": [{"id": "1", "content": "箇所A", "suggestion": "理由B"}], "overallComment": "Done"}'''
        result = parse_model_output(text)
        
        assert len(result["suggestions"]) == 1
        assert result["suggestions"][0]["original"] == "箇所A"
        assert result["suggestions"][0]["reason"] == "理由B"
    
    def test_excerpt_fix_keys(self):
        """Test that parser handles excerpt/fix as alternative field names."""
        text = '''{"suggestions": [{"id": "1", "excerpt": "抜粋", "fix": "修正"}], "overallComment": "完了"}'''
        result = parse_model_output(text)
        
        assert len(result["suggestions"]) == 1
        assert result["suggestions"][0]["original"] == "抜粋"
        assert result["suggestions"][0]["reason"] == "修正"
    
    def test_priority_original_over_text(self):
        """Test that original key takes priority over text."""
        text = '''{"suggestions": [{"original": "優先", "text": "非優先", "reason": "理由"}], "overallComment": ""}'''
        result = parse_model_output(text)
        
        assert result["suggestions"][0]["original"] == "優先"
    
    def test_missing_content_fields(self):
        """An item with no original/reason content at all is filtered out
        as a fully-blank item (2026-08 refine-suggestion-card-interactions),
        rather than surfaced as an empty suggestion with empty strings."""
        text = '''{"suggestions": [{"id": "1"}], "overallComment": ""}'''
        result = parse_model_output(text)
        
        assert result["suggestions"] == []

    # === Regression tests: truncated responses (e.g. max_tokens cutoff) ===

    def test_truncated_response_mid_string_recovers_first_item(self):
        text = '{"suggestions":[{"id":"1","original":"彼は昨日、東京に行きました","reason":"時制の誤り。過去形にすべきで'
        result = parse_model_output(text)

        assert len(result["suggestions"]) == 1
        assert result["suggestions"][0]["original"] == "彼は昨日、東京に行きました"

    def test_truncated_response_after_second_item_keeps_both(self):
        text = '{"suggestions":[{"id":"1","original":"a","reason":"b"},{"id":"2","original":"c","reason":"d"'
        result = parse_model_output(text)

        assert len(result["suggestions"]) == 2
        assert result["suggestions"][1]["original"] == "c"

    def test_truncated_immediately_after_array_open(self):
        text = '{"suggestions":['
        result = parse_model_output(text)

        assert result["suggestions"] == []

    def test_truncated_dense_response_keeps_every_complete_item(self):
        """Regression (fix-gemini-thinking-coverage-budget): with thinking
        reduced, Gemini emits far more items per response, and a live
        gemini-3.6-flash reply arrived unterminated after 17 complete items.
        Only the incomplete trailing item may be lost — earlier complete ones
        must all survive, with contiguous ids."""
        complete = ",".join(
            f'{{"id":"{i}","original":"箇所{i}","reason":"理由{i}"}}'
            for i in range(1, 18)
        )
        text = (
            '{"suggestions":[' + complete
            + ',{"id":"18","original":"箇所18","reason":"途中で切'
        )
        result = parse_model_output(text)

        # All 17 complete items survive verbatim. The partial 18th is salvaged
        # too (its `original` closed before the cutoff, so only `reason` is
        # lost), but the guarantee under test is that no *complete* item is
        # discarded and ids stay contiguous.
        assert len(result["suggestions"]) >= 17
        for i in range(1, 18):
            item = result["suggestions"][i - 1]
            assert item["id"] == str(i)
            assert item["original"] == f"箇所{i}"
            assert item["reason"] == f"理由{i}"

    # === Tests for blank-item filtering (2026-08 refine-suggestion-card-interactions) ===

    def test_fully_blank_item_is_dropped(self):
        text = '''{"suggestions": [
            {"id": "1", "original": "箇所1", "reason": "理由1"},
            {"id": "2", "original": "", "reason": ""},
            {"id": "3", "original": "箇所3", "reason": "理由3"}
        ], "overallComment": "総評"}'''
        result = parse_model_output(text)

        assert len(result["suggestions"]) == 2
        assert result["suggestions"][0]["original"] == "箇所1"
        assert result["suggestions"][1]["original"] == "箇所3"

    def test_whitespace_only_item_is_dropped(self):
        text = '''{"suggestions": [
            {"id": "1", "original": "  ", "reason": "\\n\\t "},
            {"id": "2", "original": "箇所2", "reason": "理由2"}
        ], "overallComment": "総評"}'''
        result = parse_model_output(text)

        assert len(result["suggestions"]) == 1
        assert result["suggestions"][0]["original"] == "箇所2"

    def test_ids_stay_contiguous_after_filtering_blank_item(self):
        """Regression: a blank item between two valid items must not leave
        a gap in the id sequence (e.g. ids "1", "3" instead of "1", "2")."""
        text = '''{"suggestions": [
            {"id": "1", "original": "箇所1", "reason": "理由1"},
            {"id": "2", "original": "", "reason": ""},
            {"id": "3", "original": "箇所3", "reason": "理由3"}
        ], "overallComment": "総評"}'''
        result = parse_model_output(text)

        assert [s["id"] for s in result["suggestions"]] == ["1", "2"]

    def test_item_with_only_one_blank_field_is_retained(self):
        """Only fully-blank (both fields empty) items are dropped; a
        partially-filled item is still a genuine suggestion."""
        text = '''{"suggestions": [
            {"id": "1", "original": "箇所1", "reason": ""},
            {"id": "2", "original": "", "reason": "理由2"}
        ], "overallComment": "総評"}'''
        result = parse_model_output(text)

        assert len(result["suggestions"]) == 2

    def test_no_blank_items_unaffected(self):
        text = '''{"suggestions": [
            {"id": "1", "original": "箇所1", "reason": "理由1"},
            {"id": "2", "original": "箇所2", "reason": "理由2"}
        ], "overallComment": "総評"}'''
        result = parse_model_output(text)

        assert [s["id"] for s in result["suggestions"]] == ["1", "2"]


class TestSourceExcerptField:
    """Tests for the optional `sourceExcerpt` field (highlight-suggestion-text-spans)."""

    def test_source_excerpt_extracted_when_present(self):
        text = '''{"suggestions": [{"id": "1", "original": "行きます", "reason": "时态错误", "sourceExcerpt": "行きました"}], "overallComment": "OK"}'''
        result = parse_model_output(text)

        assert len(result["suggestions"]) == 1
        assert result["suggestions"][0]["sourceExcerpt"] == "行きました"

    def test_source_excerpt_defaults_to_empty_string_when_absent(self):
        text = '''{"suggestions": [{"id": "1", "original": "良いから", "reason": "语气问题"}], "overallComment": "OK"}'''
        result = parse_model_output(text)

        assert len(result["suggestions"]) == 1
        assert result["suggestions"][0]["sourceExcerpt"] == ""

    def test_source_excerpt_defaults_to_empty_string_when_explicitly_empty(self):
        text = '''{"suggestions": [{"id": "1", "original": "とても楽しいでした", "reason": "活用错误", "sourceExcerpt": ""}], "overallComment": "OK"}'''
        result = parse_model_output(text)

        assert result["suggestions"][0]["sourceExcerpt"] == ""

    def test_source_excerpt_extracted_via_japanese_fallback_key(self):
        text = '''{"suggestions": [{"id": "1", "original": "テスト", "reason": "理由", "原文箇所": "原文の該当箇所"}], "overallComment": "OK"}'''
        result = parse_model_output(text)

        assert result["suggestions"][0]["sourceExcerpt"] == "原文の該当箇所"

    def test_source_excerpt_extracted_via_source_key(self):
        text = '''{"suggestions": [{"id": "1", "original": "テスト", "reason": "理由", "source": "対応箇所"}], "overallComment": "OK"}'''
        result = parse_model_output(text)

        assert result["suggestions"][0]["sourceExcerpt"] == "対応箇所"

    def test_source_excerpt_extracted_via_sourcetext_key(self):
        text = '''{"suggestions": [{"id": "1", "original": "テスト", "reason": "理由", "sourceText": "対応箇所2"}], "overallComment": "OK"}'''
        result = parse_model_output(text)

        assert result["suggestions"][0]["sourceExcerpt"] == "対応箇所2"

    def test_canonical_key_takes_priority_over_fallback(self):
        text = '''{"suggestions": [{"id": "1", "original": "テスト", "reason": "理由", "sourceExcerpt": "優先", "source": "非優先"}], "overallComment": "OK"}'''
        result = parse_model_output(text)

        assert result["suggestions"][0]["sourceExcerpt"] == "優先"

    def test_source_excerpt_present_on_multiple_suggestions_mixed(self):
        text = '''{"suggestions": [
            {"id": "1", "original": "箇所1", "reason": "理由1", "sourceExcerpt": "対応1"},
            {"id": "2", "original": "箇所2", "reason": "理由2"}
        ], "overallComment": "OK"}'''
        result = parse_model_output(text)

        assert result["suggestions"][0]["sourceExcerpt"] == "対応1"
        assert result["suggestions"][1]["sourceExcerpt"] == ""

    def test_source_excerpt_does_not_affect_blank_item_filtering(self):
        """An item with blank original/reason is still dropped even if it
        happens to carry a non-empty sourceExcerpt — sourceExcerpt is not
        part of the blank-item check."""
        text = '''{"suggestions": [
            {"id": "1", "original": "", "reason": "", "sourceExcerpt": "無視されるべき"},
            {"id": "2", "original": "箇所2", "reason": "理由2"}
        ], "overallComment": "OK"}'''
        result = parse_model_output(text)

        assert len(result["suggestions"]) == 1
        assert result["suggestions"][0]["original"] == "箇所2"


class TestHasNonChineseReasonExemptsSourceExcerpt:
    def test_hiragana_katakana_in_source_excerpt_does_not_trigger_retry(self):
        result = {
            "suggestions": [
                {
                    "id": "1",
                    "original": "行きます",
                    "reason": "这是中文说明",
                    "sourceExcerpt": "行きました",
                }
            ],
            "overallComment": "中文总评",
        }
        assert has_non_chinese_reason(result) is False


class TestHasNonChineseReason:
    def test_detects_hiragana_in_reason(self):
        result = {
            "suggestions": [{"id": "1", "original": "元のテキスト", "reason": "これは日本語のひらがなです"}],
            "overallComment": "总体评论正常",
        }
        assert has_non_chinese_reason(result) is True

    def test_detects_katakana_in_reason(self):
        result = {
            "suggestions": [{"id": "1", "original": "テスト", "reason": "コメントがカタカナです"}],
            "overallComment": "总体评论正常",
        }
        assert has_non_chinese_reason(result) is True

    def test_detects_hiragana_in_overall_comment(self):
        result = {
            "suggestions": [{"id": "1", "original": "テスト", "reason": "这是中文评论"}],
            "overallComment": "全体的にとても良いです",
        }
        assert has_non_chinese_reason(result) is True

    def test_pure_chinese_reason_and_comment_returns_false(self):
        result = {
            "suggestions": [
                {"id": "1", "original": "彼は昨日、東京に行きました", "reason": "这里应该用过去式，而不是现在时"},
            ],
            "overallComment": "整体表达清晰，继续保持！",
        }
        assert has_non_chinese_reason(result) is False

    def test_ignores_hiragana_katakana_in_original_field(self):
        """The `original` field must stay Japanese and is intentionally
        exempt from this check."""
        result = {
            "suggestions": [
                {"id": "1", "original": "これはひらがなとカタカナを含む日本語です", "reason": "这是中文说明"},
            ],
            "overallComment": "中文总评",
        }
        assert has_non_chinese_reason(result) is False

    def test_empty_result_returns_false(self):
        result = {"suggestions": [], "overallComment": ""}
        assert has_non_chinese_reason(result) is False

    def test_detects_halfwidth_katakana_in_reason(self):
        # Halfwidth katakana only (no fullwidth kana) — must still fail.
        result = {
            "suggestions": [
                {"id": "1", "original": "テスト", "reason": "ｺﾒﾝﾄﾊﾝｶｸ"}
            ],
            "overallComment": "中文总评",
        }
        assert has_non_chinese_reason(result) is True

    def test_detects_japanese_function_pattern_via_kana_copula(self):
        """Function-word patterns (です/ます/…) are Japanese signals."""
        result = {
            "suggestions": [
                {"id": "1", "original": "行きます", "reason": "時制が不正です"}
            ],
            "overallComment": "中文总评",
        }
        assert has_non_chinese_reason(result) is True

    def test_simplified_chinese_with_shared_hanzi_passes(self):
        """Shared Han characters must not alone fail the check."""
        result = {
            "suggestions": [
                {
                    "id": "1",
                    "original": "文法",
                    "reason": "这里的语法不自然，建议改用更常见的表达",
                }
            ],
            "overallComment": "整体意思清楚，继续保持！",
        }
        assert has_non_chinese_reason(result) is False

    def test_chinese_reason_with_double_quoted_japanese_forms_passes(self):
        """"" / “” cites of Japanese forms must not false-positive."""
        result = {
            "suggestions": [
                {
                    "id": "1",
                    "original": "行きます",
                    "reason": CASE_DOUBLE_QUOTE_COMPLIANT_REASON,
                }
            ],
            "overallComment": "整体表达清楚，继续保持！",
        }
        assert has_non_chinese_reason(result) is False

    def test_chinese_reason_with_legacy_corner_quoted_forms_still_passes_chinese_check(self):
        """Legacy 「…」 cites still strip for Chinese detect (corner check is separate)."""
        result = {
            "suggestions": [
                {
                    "id": "1",
                    "original": "行きます",
                    "reason": CASE_CORNER_QUOTE_IN_CHINESE_REASON,
                }
            ],
            "overallComment": "整体表达清楚，继续保持！",
        }
        assert has_non_chinese_reason(result) is False

    def test_japanese_prose_outside_quotes_still_fails(self):
        """Kana outside citation quotes still fails even when some spans are quoted."""
        result = {
            "suggestions": [
                {
                    "id": "1",
                    "original": "行きます",
                    "reason": "“行きます”という表現は不自然です",
                }
            ],
            "overallComment": "中文总评",
        }
        assert has_non_chinese_reason(result) is True


class TestHasJapaneseCornerQuotesInCritique:
    """Misuse detector: Chinese prose in 「」 retries; JP TARGET cites OK."""

    def test_jp_cite_corner_quotes_in_reason_allowed(self):
        """「昨日」「行きました」 are JP cites — must not trip retry."""
        result = {
            "suggestions": [
                {
                    "id": "1",
                    "original": "行きます",
                    "reason": CASE_CORNER_QUOTE_IN_CHINESE_REASON,
                }
            ],
            "overallComment": "中文总评",
        }
        assert has_japanese_corner_quotes_in_critique(result) is False

    def test_gemini_style_academic_term_cite_allowed(self):
        from tests.fixtures.gemini_quality_bar_cases import (
            QUALITY_BAR_COMPLIANT_REASON,
            QUALITY_BAR_COMPLIANT_OVERALL,
        )

        result = {
            "suggestions": [
                {
                    "id": "1",
                    "original": "史詩",
                    "reason": QUALITY_BAR_COMPLIANT_REASON,
                }
            ],
            "overallComment": QUALITY_BAR_COMPLIANT_OVERALL,
        }
        assert has_japanese_corner_quotes_in_critique(result) is False

    def test_double_quote_reason_passes(self):
        result = {
            "suggestions": [
                {
                    "id": "1",
                    "original": "行きます",
                    "reason": CASE_DOUBLE_QUOTE_COMPLIANT_REASON,
                }
            ],
            "overallComment": "整体清楚",
        }
        assert has_japanese_corner_quotes_in_critique(result) is False

    def test_chinese_prose_corner_quotes_in_overall_detected(self):
        result = {
            "suggestions": [
                {
                    "id": "1",
                    "original": "行きます",
                    "reason": CASE_DOUBLE_QUOTE_COMPLIANT_REASON,
                }
            ],
            "overallComment": "存在「时态」问题",
        }
        assert has_japanese_corner_quotes_in_critique(result) is True

    def test_chinese_prose_corner_misuse_in_reason_detected(self):
        from tests.fixtures.gemini_quality_bar_cases import (
            QUALITY_BAR_CN_PROSE_CORNER_MISUSE,
        )

        result = {
            "suggestions": [
                {
                    "id": "1",
                    "original": "行きます",
                    "reason": QUALITY_BAR_CN_PROSE_CORNER_MISUSE,
                }
            ],
            "overallComment": "中文总评",
        }
        assert has_japanese_corner_quotes_in_critique(result) is True


class TestHasWeakCritiqueReason:
    """Regression aid for Spec MUST why-in-reason (not wired into retry)."""

    def test_case_b_weak_location_only_fails(self):
        result = {
            "suggestions": [
                {
                    "id": "1",
                    "original": CASE_B_TARGET_TEXT[:20],
                    "reason": CASE_B_WEAK_REASON,
                    "sourceExcerpt": "",
                }
            ],
            "overallComment": "中文总评",
        }
        assert has_weak_critique_reason(result) is True

    def test_case_b_legacy_corner_weak_also_fails(self):
        result = {
            "suggestions": [
                {
                    "id": "1",
                    "original": "誰でも",
                    "reason": CASE_B_WEAK_REASON_LEGACY_CORNER,
                    "sourceExcerpt": "",
                }
            ],
            "overallComment": "中文总评",
        }
        assert has_weak_critique_reason(result) is True

    def test_case_b_compliant_reason_with_why_passes(self):
        result = {
            "suggestions": [
                {
                    "id": "1",
                    "original": "誰でも",
                    "reason": CASE_B_COMPLIANT_REASON,
                    "sourceExcerpt": "",
                }
            ],
            "overallComment": "中文总评",
        }
        assert has_weak_critique_reason(result) is False

    def test_case_a_bad_reason_pattern_is_documented_false_positive(self):
        """Case A documents invented 缺少"が"; heuristic flags location-only shape."""
        assert "ができなかったが" in CASE_A_TARGET_TEXT
        assert CASE_A_BAD_REASON.startswith("缺少")
        assert "false" in CASE_A_NOTES.lower() or "invent" in CASE_A_NOTES.lower()
        result = {
            "suggestions": [
                {
                    "id": "1",
                    "original": "できなかったが",
                    "reason": CASE_A_BAD_REASON,
                    "sourceExcerpt": "",
                }
            ],
            "overallComment": "中文总评",
        }
        # Location-only 缺少 without 为什么 → weak (quality non-compliant).
        assert has_weak_critique_reason(result) is True
        assert has_weak_critique_reason(
            {
                "suggestions": [
                    {
                        "id": "1",
                        "original": "できなかったが",
                        "reason": CASE_A_BAD_REASON_LEGACY_CORNER,
                    }
                ],
                "overallComment": "",
            }
        ) is True

    def test_case_c_drift_reason_is_documented(self):
        assert "シナリオを覚えない" in CASE_C_TARGET_TEXT
        assert "落下剧情" in CASE_C_BAD_REASON
        assert "drift" in CASE_C_NOTES.lower()
        # Not a location-only 缺少 pattern — weak heuristic does not apply;
        # quality expectation is prompt + fixture documentation.
        result = {
            "suggestions": [
                {
                    "id": "1",
                    "original": "シナリオを覚えないのだ",
                    "reason": CASE_C_BAD_REASON,
                }
            ],
            "overallComment": "中文总评",
        }
        assert has_weak_critique_reason(result) is False
        assert has_japanese_corner_quotes_in_critique(result) is False

    def test_few_shot_style_reason_with_why_is_not_weak(self):
        result = {
            "suggestions": [
                {
                    "id": "1",
                    "original": "行きます",
                    "reason": CASE_DOUBLE_QUOTE_COMPLIANT_REASON,
                    "sourceExcerpt": "行きました",
                }
            ],
            "overallComment": "整体清楚",
        }
        assert has_weak_critique_reason(result) is False

    def test_empty_suggestions_not_weak(self):
        assert has_weak_critique_reason({"suggestions": [], "overallComment": ""}) is False
