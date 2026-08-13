"""
Output parsing for LLM responses.
Ported from frontend/src/lib/webllm/parser.ts.

Hardened to handle common LLM output issues:
- Trailing commas in arrays/objects
- Truncated JSON (incomplete arrays/objects)
- Markdown code fences wrapping JSON
- Preamble/postamble text around JSON
- Both Japanese (指摘/全体講評) and English (suggestions/overallComment) keys

This parser's JSON-structure handling (extract/repair/field-fallback) is
field-content-language-agnostic: it extracts whatever string values are
present in the `original`/`reason` (or their Japanese/legacy field-name
equivalents) and `overallComment` keys without transforming their language.
As of 2026-08 the prompts (see backend/app/llm/prompts.py) instruct the
model to write `original` in Japanese and `reason`/`overallComment` in
Simplified Chinese. This module additionally exposes `has_non_chinese_reason()`,
a separate, opt-in content-language check (Hiragana/Katakana/halfwidth kana
plus Japanese function-word patterns; see `enforce-chinese-suggestion-comments`)
that callers such as backend/app/llm/suggestions.py use to decide whether to
retry generation — `parse_model_output()` itself still does not validate or
reject based on language, it only structures the JSON.

`parse_model_output()` also drops suggestion items whose `original` and
`reason` are both empty/whitespace-only after parsing, re-sequencing the
remaining items' `id`s contiguously, so a model's occasional blank filler
item never surfaces as an empty suggestion card.

As of 2026-08 (`highlight-suggestion-text-spans` change), each suggestion
also carries an optional `sourceExcerpt` field: an excerpt from SOURCE TEXT
corresponding to the flagged TARGET TEXT snippet, extracted with the same
multi-key-fallback approach as `original`/`reason` and defaulting to `""`
when absent. Like `original`, it is expected to stay in SOURCE TEXT's
language (Japanese) and is intentionally exempt from `has_non_chinese_reason()`.

As of `harden-semantic-suggestion-reasons` (2026-08), Spec MUST requires every
`reason`（指摘コメント）to include why the correction is needed (all critique
types). That MUST is primarily enforced via prompts. This module also exposes
`has_weak_critique_reason()` — a narrow regression heuristic for location-only
「缺少「X」在…」 reasons that omit necessity cues. It is intentionally NOT
wired into `generate_suggestions()` retry (too noisy for production); use it
in tests/fixtures.
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
    sourceExcerpt: str


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
    - sourceExcerpt: sourceExcerpt, 原文箇所, source, sourceText (defaults to "" when absent)
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
    blank_items_skipped = 0
    for item in shiteki_list:
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
            original = str(original)
            reason = str(reason)

            # Optional: excerpt from SOURCE TEXT corresponding to `original`
            # (a TARGET TEXT excerpt). Absent/omitted when the model found no
            # clear correspondence (see prompts.py) — defaults to "", never
            # fabricated. Not part of the blank-item check below since an
            # empty sourceExcerpt is an expected, valid value, not a signal
            # that the whole item is filler.
            source_excerpt = (
                item.get("sourceExcerpt") or
                item.get("原文箇所") or
                item.get("source") or
                item.get("sourceText") or
                ""
            )
            source_excerpt = str(source_excerpt)

            # The model occasionally emits one extra, fully-blank item (e.g.
            # padding/formatting artifact). Skip it rather than surfacing an
            # empty "Option" card; ids below are assigned post-filter so they
            # stay contiguous instead of leaving a gap at the dropped index.
            if not original.strip() and not reason.strip():
                blank_items_skipped += 1
                continue

            suggestions.append({
                "id": str(len(suggestions) + 1),
                "original": original,
                "reason": reason,
                "sourceExcerpt": source_excerpt,
            })

    if blank_items_skipped:
        logger.info(f"[parser] Skipped {blank_items_skipped} fully-blank suggestion item(s)")

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


# Japanese-script / Japanese-prose signals for explanation fields that must
# be Simplified Chinese. See `enforce-chinese-suggestion-comments` design.md.
#
# 1) Hiragana (U+3040-U+309F), Katakana (U+30A0-U+30FF), halfwidth Katakana
#    (U+FF66-U+FF9D): never appear in Chinese *prose*.
# 2) Common Japanese particle / function-word patterns (all contain kana, so
#    they overlap with (1) for dense Japanese, but make the intent explicit
#    and catch mixed strings in tests/docs). Do NOT use Han-only compounds
#    that also appear in Simplified Chinese — that would false-positive.
#
# Quoted Japanese forms inside 「…」/『…』 are stripped before the check so
# legitimate Chinese explanations that cite TARGET TEXT (as the few-shot
# demonstrates) are not false-positive retries. Kana / function words
# *outside* those quotes still fail.
_JAPANESE_KANA_PATTERN = re.compile(r'[\u3040-\u30FF\uFF66-\uFF9D]')
_JAPANESE_FUNCTION_PATTERN = re.compile(
    r'(?:です|ます|でした|ました|ません|である|だった|ではない|ではありません|'
    r'してください|しています|していない|ことができる|ことになる|'
    r'べきだ|べきで|という|について|に対して|として|'
    r'のです|なので|ですが|ますが)'
)
# Corner-bracket quotes used when Chinese reasons cite Japanese forms.
_QUOTED_JP_SPAN_PATTERN = re.compile(r'[「『].*?[」』]', re.DOTALL)


def _strip_quoted_japanese_spans(text: str) -> str:
    """Remove 「…」/『…』 spans so cited Japanese forms do not trip the check."""
    return _QUOTED_JP_SPAN_PATTERN.sub("", text)


def _text_looks_japanese(text: str) -> bool:
    """True if explanatory prose (outside 「」/『』 cites) looks Japanese."""
    if not text:
        return False
    prose = _strip_quoted_japanese_spans(text)
    if not prose.strip():
        # Entirely quoted — no Chinese explanation left; treat as non-Chinese.
        return True
    if _JAPANESE_KANA_PATTERN.search(prose):
        return True
    return bool(_JAPANESE_FUNCTION_PATTERN.search(prose))


def has_non_chinese_reason(result: ParsedResponse) -> bool:
    """
    True if any suggestion's `reason` or the top-level `overallComment`
    looks Japanese (kana / halfwidth kana / Japanese function words outside
    「」/『』 citation spans), indicating that field was written in Japanese
    rather than the required Simplified Chinese.

    Pure Simplified Chinese that shares Han characters with Japanese kanji
    MUST pass (returns False). Chinese explanations that quote Japanese
    forms inside 「…」/『…』 MUST also pass. The `original` and
    `sourceExcerpt` fields are intentionally NOT checked — both are
    required to stay in Japanese.

    Used by backend/app/llm/suggestions.py to decide whether a generate+parse
    attempt should be retried, composing with (not replacing)
    `is_json_extraction_failure`, both bounded by the same
    MAX_PARSE_RETRY_ATTEMPTS budget.
    """
    if _text_looks_japanese(result["overallComment"]):
        return True
    return any(
        _text_looks_japanese(suggestion["reason"])
        for suggestion in result["suggestions"]
    )


# Narrow "location-only missing form" shape: 缺少「X」在… (or 缺少『X』在…).
_WEAK_QUE_SHAO_LOCATION = re.compile(
    r"缺少[「『][^」』]+[」』]在"
)

# Necessity / why cues — if any appear, treat as explaining 为什么.
_WHY_NECESSITY_MARKERS = re.compile(
    r"(因为|因此|由于|必须|需要|用于|表示|才能|否则|为了|"
    r"语感|对比|强调|主题|应[该当]?|建议|改用|不自然|错误|"
    r"不通|无法|矛盾|限定|焦点|更自然|更委婉|更流畅|语法不通)"
)


def _reason_is_weak_location_only(reason: str) -> bool:
    """True if reason looks like location-only 「缺少「X」在…」 without 为什么."""
    text = (reason or "").strip()
    if not text:
        return False
    if not _WEAK_QUE_SHAO_LOCATION.search(text):
        return False
    return _WHY_NECESSITY_MARKERS.search(text) is None


def has_weak_critique_reason(result: ParsedResponse) -> bool:
    """
    True if any suggestion's `reason` matches a weak location-only
    「缺少「X」在…」 pattern without necessity/why markers.

    Spec MUST (`harden-semantic-suggestion-reasons`): every critique `reason`
    must include why the correction is needed. That MUST is primarily
    prompt-enforced. This heuristic is a CI/regression aid for Case B–style
    weak reasons and is NOT used by `generate_suggestions()` retry (design:
    too noisy for production). Does not inspect `overallComment`, `original`,
    or `sourceExcerpt`.
    """
    return any(
        _reason_is_weak_location_only(suggestion["reason"])
        for suggestion in result["suggestions"]
    )
