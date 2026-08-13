"""
Semantic critique-quality fixtures (harden-semantic-suggestion-reasons).

Case A — false / wrong particle inventing:
  TARGET is already acceptable Japanese; a model reason claiming
  缺少"が"在"できなかった"后 is a documented false positive.

Case B — why missing from 指摘コメント:
  Spec MUST: every reason must include why the correction is needed.
  Location-only 缺少"は"在"誰でも"前 without 为什么 is non-compliant.

Case C — meaning / wording drift:
  Awkward JP vs SOURCE meaning must not be “fixed” with a rewrite that
  drifts (e.g. toward 听众一听就知道大概，不会落下剧情) without accurate why.

Manual verify (UI /api/suggestions):
  1. Paste Case A TARGET → confirm no false 缺少"が" inventing.
  2. Paste Case B TARGET → if particle critique appears, reason includes why
     in accessible Chinese; Chinese meta uses "" / “”; JP forms MAY use 「」.
  3. Paste Case C TARGET (+ CN SOURCE if available) → meaning critiques quote
     SOURCE accurately; no drift rewrite; accessible why.
  4. Multi-paragraph TARGET → issues appear across paragraphs when real.
  5. Spot-check reasons are understandable without JP↔CN craft knowledge.

See also gemini_quality_bar_cases.py for Gemini-style 現状→推奨 shapes
and epic SOURCE/TARGET manual paste (`raise-suggestion-quality-to-gemini-bar`).
"""

# --- Case A -----------------------------------------------------------------

CASE_A_TARGET_TEXT = (
    "多くの芸人は文字を読むことができなかったが、長い詩を吟唱することができる"
)

# Documented unacceptable false-positive reason (invented particle).
CASE_A_BAD_REASON = '缺少"が"在"できなかった"后'
CASE_A_BAD_REASON_LEGACY_CORNER = "缺少「が」在「できなかった」后"

CASE_A_NOTES = (
    "Japanese already uses contrastive が after できなかった; inventing "
    "another が is a false 缺少 critique and must not be treated as "
    "acceptable quality."
)

# --- Case B -----------------------------------------------------------------

CASE_B_TARGET_TEXT = (
    "彼らの語りは、演じる場所によって誰でもはっきり聞こえるとは限らない"
)

# Location-only — fails Spec MUST why-in-reason / has_weak_critique_reason.
CASE_B_WEAK_REASON = '缺少"は"在"誰でも"前'
CASE_B_WEAK_REASON_LEGACY_CORNER = "缺少「は」在「誰でも」前"

# Compliant shape: what/where + why (必要性), Chinese curly quotes.
CASE_B_COMPLIANT_REASON = (
    "缺少“は”在“誰でも”前，因为需要用助词“は”标出对比主题，"
    "强调“并非任何人都能听清”这一限定，否则句子缺少对比焦点，读者容易听成"
    "“谁都能听清”的意思"
)

# --- Case C — meaning / wording drift ---------------------------------------

CASE_C_TARGET_TEXT = (
    "歴史物語による常套語は、ことわざのように、来場者が聞くと粗筋が分かるから、"
    "シナリオを覚えないのだ"
)

# Weak/wrong: labels awkwardness and drifts rewrite away from SOURCE meaning.
CASE_C_BAD_REASON = (
    "“シナリオを覚えない”说法别扭，应改成“听众一听就知道大概，不会落下剧情”"
)

CASE_C_NOTES = (
    "Critiquing awkward JP vs SOURCE must explain the meaning problem "
    "accurately; proposing a rewrite that drifts (落下剧情) without faithful "
    "SOURCE alignment is non-compliant."
)

# --- Quote-mark / accessibility documentation -------------------------------

CASE_CORNER_QUOTE_IN_CHINESE_REASON = (
    "「昨日」表示过去，因此必须用过去式「行きました」"
)

CASE_DOUBLE_QUOTE_COMPLIANT_REASON = (
    "“昨日”表示过去发生的事，因此必须用过去式“行きました”，"
    "否则时间与动词时态矛盾，读者会以为事情还没发生"
)
