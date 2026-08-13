"""
Teaching-quality critique shapes (improve-suggestion-teaching-quality).

Documents anti-patterns to reject and compliant teaching-oriented reasons.
CI MUST NOT call a live LLM — regression / manual-verify references only.

See also gemini_quality_bar_cases.py for structural Gemini-bar shapes
(strengths→gaps, 現状→推奨, quote policy).

Manual verify (UI /api/suggestions — Groq/CF; not Gemini provider; not WebLLM
unless オフラインモード is ON):
  1. Paste QUALITY_BAR_SOURCE_TEXT / QUALITY_BAR_TARGET_TEXT (or short pair)
     from gemini_quality_bar_cases into 原文 / 添削対象.
  2. Prefer essential issues over cosmetic “可省略…” surface edits.
  3. Lexical upgrades should contrast current vs recommended nuance, then
     necessity — not bare “原文说了X所以改成Y” or vague “更能体现…”.
  4. Spelling / domain-term reasons should mention lasting competence impact
     when applicable.
"""

from .gemini_quality_bar_cases import (
    QUALITY_BAR_SHORT_SOURCE,
    QUALITY_BAR_SHORT_TARGET,
    QUALITY_BAR_SOURCE_TEXT,
    QUALITY_BAR_TARGET_TEXT,
)

# Re-export corpora pointers for convenience.
TEACHING_SOURCE_TEXT = QUALITY_BAR_SOURCE_TEXT
TEACHING_TARGET_TEXT = QUALITY_BAR_TARGET_TEXT
TEACHING_SHORT_SOURCE = QUALITY_BAR_SHORT_SOURCE
TEACHING_SHORT_TARGET = QUALITY_BAR_SHORT_TARGET

# --- Anti-patterns (non-compliant; documentation / negative examples) ---

# 1) Trivial surface omit as the main point.
TEACHING_BAD_TRIVIAL_SURFACE = (
    "紙に印刷された文字 → 「印刷された文字」：可以省略“紙に”，更合日语习惯、更简洁"
)

# 2) Bare SOURCE-token swap without pedagogy.
TEACHING_BAD_SOURCE_TOKEN_SWAP = (
    "決まり文句 → 「套语」：因为原文写的是“套语”，所以应改成套语"
)

# 3) Preference without contrastive nuance.
TEACHING_BAD_PREFERENCE_NO_CONTRAST = (
    "唱える → 「演唱する」：更能体现口头传统"
)

# --- Compliant teaching-oriented shapes ---

# Contrastive lexical / register (current vs recommended nuance, then why).
TEACHING_GOOD_CONTRASTIVE_REASON = (
    "でも → 「しかし」：「でも」偏日常口语转折，读起来像会话；「しかし」是书面"
    "论述转折。本文是学术随笔开篇，应用后者，否则语域掉到口语，影响今后同类"
    "论述译的语体判断"
)

# Class-of-error why (domain term / competence for future translations).
TEACHING_GOOD_CLASS_OF_ERROR_REASON = (
    "史詩 → 「叙事詩」（じょじし）：「史詩」像未消化的中文词形；日语社科/文学里"
    "“史诗”的规范译词是「叙事詩」。混用会暴露领域译词基础不足，后续译文也容易"
    "继续写错专名"
)

# Contrastive modality / sense (illustrative shape; not tied to short few-shot).
TEACHING_GOOD_MODALITY_REASON = (
    "見落とす → 「聞き漏らす」：「見落とす」强调视觉上没看见；「聞き漏らす」"
    "强调听觉上没听见。原文写的是听漏声音传统，用视觉动词会造成情态错位，"
    "今后遇到视听转换时也会继续用错感官动词"
)

TEACHING_QUALITY_NOTES = (
    "Teaching bar is prompt-shaped (Groq/CF/WebLLM). Do not require live LLM "
    "in CI. Reject trivial surface, bare source-swap, preference-without-contrast; "
    "prefer essential gaps + contrastive nuance + class-of-error why."
)
