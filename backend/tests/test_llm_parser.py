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
        text = '''{"指摘": [{"番号": 1}], "全体講評": ""}'''
        result = parse_model_output(text)
        
        assert len(result["suggestions"]) == 1
        assert result["suggestions"][0]["original"] == ""
        assert result["suggestions"][0]["reason"] == ""
    
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
        """Test that missing content fields result in empty strings."""
        text = '''{"suggestions": [{"id": "1"}], "overallComment": ""}'''
        result = parse_model_output(text)
        
        assert len(result["suggestions"]) == 1
        assert result["suggestions"][0]["original"] == ""
        assert result["suggestions"][0]["reason"] == ""

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
