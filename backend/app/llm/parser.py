"""
Output parsing for LLM responses.
Ported from frontend/src/lib/webllm/parser.ts.

Hardened to handle common LLM output issues:
- Trailing commas in arrays/objects
- Truncated JSON (incomplete arrays/objects)
- Markdown code fences wrapping JSON
- Preamble/postamble text around JSON
"""

from __future__ import annotations

import re
import json
from typing import TypedDict, Optional, List, Dict, Any


class CorrectionSuggestion(TypedDict):
    id: str
    original: str
    reason: str


class ParsedResponse(TypedDict):
    suggestions: List[CorrectionSuggestion]
    overallComment: str


def remove_trailing_commas(json_str: str) -> str:
    """Remove trailing commas from JSON string."""
    json_str = re.sub(r',\s*]', ']', json_str)
    json_str = re.sub(r',\s*}', '}', json_str)
    return json_str


def strip_markdown_fences(text: str) -> str:
    """Strip markdown code fences from text."""
    text = re.sub(r'```json\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'```\s*', '', text)
    return text


def repair_truncated_json(json_str: str) -> str:
    """Attempt to repair truncated JSON by closing open brackets/braces."""
    repaired = json_str
    
    open_brackets = repaired.count('[')
    close_brackets = repaired.count(']')
    open_braces = repaired.count('{')
    close_braces = repaired.count('}')
    
    repaired = re.sub(r',\s*$', '', repaired)
    repaired = re.sub(r':\s*$', ': null', repaired)
    repaired = re.sub(r':\s*"[^"]*$', ': ""', repaired)
    
    missing_brackets = open_brackets - close_brackets
    missing_braces = open_braces - close_braces
    
    for _ in range(missing_brackets):
        repaired += ']'
    for _ in range(missing_braces):
        repaired += '}'
    
    return repaired


def extract_json(text: str) -> Optional[str]:
    """Extract JSON object from text, trying multiple strategies."""
    match1 = re.search(r'\{\s*"指摘".*\}', text, re.DOTALL)
    if match1:
        return match1.group(0)
    
    first_brace = text.find('{')
    last_brace = text.rfind('}')
    if first_brace != -1 and last_brace > first_brace:
        return text[first_brace:last_brace + 1]
    
    if first_brace != -1:
        return text[first_brace:]
    
    return None


def safe_json_parse(text: str) -> Optional[Dict[str, Any]]:
    """Safely parse JSON with repair attempts."""
    cleaned = strip_markdown_fences(text)
    json_str = extract_json(cleaned)
    if not json_str:
        return None
    
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        pass
    
    try:
        no_trailing_commas = remove_trailing_commas(json_str)
        return json.loads(no_trailing_commas)
    except json.JSONDecodeError:
        pass
    
    try:
        repaired = remove_trailing_commas(json_str)
        repaired = repair_truncated_json(repaired)
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass
    
    return None


def parse_model_output(text: str) -> ParsedResponse:
    """
    Parse LLM model output into structured suggestions.
    Matches frontend parseModelOutput behavior.
    
    HARDENED: Never raises - returns empty on parse failure.
    """
    parsed = safe_json_parse(text)
    
    if not parsed:
        return {
            "suggestions": [],
            "overallComment": "AIの応答からJSONを抽出できませんでした。再度お試しください。",
        }
    
    shiteki_list = parsed.get("指摘", [])
    if not isinstance(shiteki_list, list):
        shiteki_list = []
    
    overall_comment = parsed.get("全体講評", "")
    if not isinstance(overall_comment, str):
        overall_comment = ""
    
    suggestions: List[CorrectionSuggestion] = []
    for i, item in enumerate(shiteki_list):
        if item and isinstance(item, dict):
            suggestions.append({
                "id": str(i + 1),
                "original": str(item.get("箇所", "")),
                "reason": str(item.get("コメント", "")),
            })
    
    return {
        "suggestions": suggestions,
        "overallComment": overall_comment,
    }
