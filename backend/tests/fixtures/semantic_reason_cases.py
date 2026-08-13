"""
Semantic critique-quality fixtures (harden-semantic-suggestion-reasons).

Case A — false / wrong particle inventing:
  TARGET is already acceptable Japanese; a model reason claiming
  缺少「が」在「できなかった」后 is a documented false positive.

Case B — why missing from 指摘コメント:
  Spec MUST: every reason must include why the correction is needed.
  Location-only 「缺少「は」在「誰でも」前」 without 为什么 is non-compliant.

Manual verify (UI /api/suggestions):
  1. Paste Case A TARGET (and any short SOURCE) → generate; confirm the
     system does not invent that false 「缺少「が」」 critique (or that a
     similar false particle inventing is rare after prompt hardening).
  2. Paste Case B TARGET → if a particle 「は」 suggestion appears, its
     Chinese reason must include why (not only where).
"""

# --- Case A -----------------------------------------------------------------

CASE_A_TARGET_TEXT = (
    "多くの芸人は文字を読むことができなかったが、長い詩を吟唱することができる"
)

# Documented unacceptable false-positive reason (invented particle).
CASE_A_BAD_REASON = "缺少「が」在「できなかった」后"

CASE_A_NOTES = (
    "Japanese already uses contrastive が after できなかった; inventing "
    "another が is a false 「缺少」 critique and must not be treated as "
    "acceptable quality."
)

# --- Case B -----------------------------------------------------------------

CASE_B_TARGET_TEXT = (
    "彼らの語りは、演じる場所によって誰でもはっきり聞こえるとは限らない"
)

# Location-only — fails Spec MUST why-in-reason / has_weak_critique_reason.
CASE_B_WEAK_REASON = "缺少「は」在「誰でも」前"

# Compliant shape: what/where + why (必要性).
CASE_B_COMPLIANT_REASON = (
    "缺少「は」在「誰でも」前，因为需要用助词「は」标出对比主题，"
    "强调“并非任何人都能听清”这一限定，否则句子缺少对比焦点"
)
