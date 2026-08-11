"""
Output parsing for LLM responses.
Ported from frontend/src/lib/webllm/parser.ts.

Hardened to handle common LLM output issues:
- Trailing commas in arrays/objects
- Truncated JSON (incomplete arrays/objects)
- Markdown code fences wrapping JSON
- Preamble/postamble text around JSON
- Both Japanese (指摘/全体講評) and English (suggestions/overallComment) keys

This parser is field-content-language-agnostic: it extracts whatever string
values are present in the `original`/`reason` (or their Japanese/legacy
field-name equivalents) and `overallComment` keys without validating or
transforming their language. As of 2026-08 the prompts (see
backend/app/llm/prompts.py) instruct the model to write `original` in
Japanese and `reason`/`overallComment` in Simplified Chinese — this parser
does not need to change for that split since it only handles JSON
structure, not content language.
"""

from __future__ import annotations

import re
import json
import logging
from typing import TypedDict, Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# Exact placeholder message returned in `overallComment` when JSON extraction
# from the raw model output fails entirely (as opposed to a genuinely valid
# response with zero suggestions). Exposed as a constant so callers (e.g.
# backend/app/llm/suggestions.py's parse-failure retry loop, and the
# frontend's `isParseFailure` check) can detect this specific failure mode
# without re-deriving/duplicating the string.
JSON_EXTRACTION_FAILURE_MESSAGE = "AIの応答からJSONを抽出できませんでした。再度お試しください。"


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
    """
    Attempt to repair truncated JSON by closing open brackets/braces.

    Closing punctuation must be appended in LIFO (stack) order matching the
    actual nesting, not just "all missing ']' then all missing '}'" — for a
    truncated `{"suggestions":[{"original":"..."` the correct close sequence
    is `}]}` (close inner object, then array, then outer object), not `]}}`.
    A naive count-based approach produces the wrong order for any JSON nested
    more than one level deep, which is always the case for our
    `{"suggestions": [{...}]}` response shape.
    """
    repaired = re.sub(r',\s*$', '', json_str)
    repaired = re.sub(r':\s*$', ': null', repaired)
    repaired = re.sub(r':\s*"[^"]*$', ': ""', repaired)

    # Walk the string tracking open bracket/brace nesting, ignoring any
    # bracket-like characters that appear inside string literals.
    stack: List[str] = []
    in_string = False
    escaped = False
    for ch in repaired:
        if in_string:
            if escaped:
                escaped = False
            elif ch == '\\':
                escaped = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
        elif ch in '{[':
            stack.append(ch)
        elif ch in '}]':
            if stack:
                stack.pop()

    # Truncation mid-string that the regexes above didn't catch (e.g. not
    # immediately preceded by a colon) — close the dangling string first.
    if in_string:
        repaired += '"'

    closing = {'{': '}', '[': ']'}
    for opener in reversed(stack):
        repaired += closing[opener]

    return repaired


def extract_json(text: str) -> Optional[str]:
    """
    Extract a JSON object from text, trying multiple strategies.

    The main strategy scans from the first '{' tracking brace nesting depth
    (ignoring braces inside string literals) to find the *matching* closing
    brace, rather than naively using the text's last '}'. This matters for
    truncated responses: if the JSON is cut off mid-response, the last '}'
    in the text may belong to an inner object (e.g. the first item of a
    `suggestions` array) rather than the outer object, and naively slicing
    to it silently drops everything after — including later array items.
    When no matching close is found (genuinely truncated), the full
    remainder is returned so repair_truncated_json can close it correctly.
    """
    match1 = re.search(r'\{\s*"指摘".*\}', text, re.DOTALL)
    if match1:
        return match1.group(0)

    first_brace = text.find('{')
    if first_brace == -1:
        return None

    depth = 0
    in_string = False
    escaped = False
    for i in range(first_brace, len(text)):
        ch = text[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == '\\':
                escaped = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
        elif ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return text[first_brace:i + 1]

    # Braces never balanced out — truncated response; return everything
    # from the first '{' onward so repair_truncated_json can close it.
    return text[first_brace:]


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
    1. Japanese keys (legacy): {"指摘": [...], "全体講評": "..."}
    2. English keys (canonical, per prompt): {"suggestions": [...], "overallComment": "..."}
    
    Item field fallbacks (tries in order):
    - original: original, 箇所, text, content, excerpt
    - reason: reason, コメント, comment, suggestion, fix
    """
    logger.debug(f"[parser] Raw input (first 500 chars): {text[:500]}")
    
    parsed = safe_json_parse(text)
    
    if not parsed:
        logger.warning(f"[parser] Failed to extract JSON from response. Raw text (first 1000 chars): {text[:1000]!r}")
        return {
            "suggestions": [],
            "overallComment": JSON_EXTRACTION_FAILURE_MESSAGE,
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
            # Try multiple possible field names for robustness
            # Models may use: original, text, content, excerpt, 箇所
            original = (
                item.get("original") or 
                item.get("箇所") or 
                item.get("text") or 
                item.get("content") or 
                item.get("excerpt") or 
                ""
            )
            # Models may use: reason, comment, suggestion, fix, コメント
            reason = (
                item.get("reason") or 
                item.get("コメント") or 
                item.get("comment") or 
                item.get("suggestion") or 
                item.get("fix") or 
                ""
            )
            
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


def is_json_extraction_failure(result: ParsedResponse) -> bool:
    """
    True if `result` is the specific "could not extract JSON" placeholder
    produced by parse_model_output(), as opposed to a genuinely valid
    response with zero suggestions (e.g. clean text with no issues found).

    Used by backend/app/llm/suggestions.py to decide whether a generate+parse
    attempt should be retried (see MAX_PARSE_RETRY_ATTEMPTS there).
    """
    return not result["suggestions"] and result["overallComment"] == JSON_EXTRACTION_FAILURE_MESSAGE
