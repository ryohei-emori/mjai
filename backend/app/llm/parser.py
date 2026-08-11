"""
Output parsing for LLM responses.
Ported from frontend/src/lib/webllm/parser.ts.

Hardened to handle common LLM output issues:
- Trailing commas in arrays/objects
- Truncated JSON (incomplete arrays/objects)
- Markdown code fences wrapping JSON
- Preamble/postamble text around JSON
- Both Japanese (指摘/全体講評) and English (suggestions/overallComment) keys
"""

from __future__ import annotations

import re
import json
import logging
from typing import TypedDict, Optional, List, Dict, Any

logger = logging.getLogger(__name__)


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
    
    Supports two key formats:
    1. Japanese keys (preferred prompt format): {"指摘": [...], "全体講評": "..."}
       - Item keys: {"番号", "箇所", "コメント"}
    2. English keys (some models output this): {"suggestions": [...], "overallComment": "..."}
       - Item keys: {"id", "original", "reason"}
    """
    logger.debug(f"[parser] Raw input (first 500 chars): {text[:500]}")
    
    parsed = safe_json_parse(text)
    
    if not parsed:
        logger.warning("[parser] Failed to extract JSON from response")
        return {
            "suggestions": [],
            "overallComment": "AIの応答からJSONを抽出できませんでした。再度お試しください。",
        }
    
    logger.debug(f"[parser] Parsed JSON keys: {list(parsed.keys())}")
    
    # Try Japanese keys first (expected from prompt), then English keys (fallback)
    shiteki_list = parsed.get("指摘")
    if shiteki_list is None:
        shiteki_list = parsed.get("suggestions", [])
        logger.debug("[parser] Using English 'suggestions' key")
    else:
        logger.debug("[parser] Using Japanese '指摘' key")
    
    if not isinstance(shiteki_list, list):
        logger.warning(f"[parser] suggestions/指摘 is not a list: {type(shiteki_list)}")
        shiteki_list = []
    
    # Try Japanese key first, then English
    overall_comment = parsed.get("全体講評")
    if overall_comment is None:
        overall_comment = parsed.get("overallComment", "")
        logger.debug("[parser] Using English 'overallComment' key")
    else:
        logger.debug("[parser] Using Japanese '全体講評' key")
    
    if not isinstance(overall_comment, str):
        overall_comment = str(overall_comment) if overall_comment else ""
    
    suggestions: List[CorrectionSuggestion] = []
    for i, item in enumerate(shiteki_list):
        if item and isinstance(item, dict):
            # Try Japanese keys first, then English
            original = item.get("箇所") or item.get("original", "")
            reason = item.get("コメント") or item.get("reason", "")
            
            suggestions.append({
                "id": str(i + 1),
                "original": str(original),
                "reason": str(reason),
            })
    
    logger.info(f"[parser] Parsed {len(suggestions)} suggestions, overallComment length: {len(overall_comment)}")
    
    # If JSON was parsed but no suggestions found, provide diagnostic message
    if not suggestions and shiteki_list:
        logger.warning(f"[parser] Items found but no valid suggestions extracted. Sample item: {shiteki_list[0] if shiteki_list else 'N/A'}")
    
    return {
        "suggestions": suggestions,
        "overallComment": overall_comment,
    }
