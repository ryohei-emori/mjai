"""
Tests for backend/app/llm/parser.py
"""

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
