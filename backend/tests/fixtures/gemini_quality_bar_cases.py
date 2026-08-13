"""
Gemini-style suggestion quality bar (raise-suggestion-quality-to-gemini-bar).

Documents desired critique *shapes* for CN→JP literary/academic translation
review. CI MUST NOT call a live LLM — these strings are regression /
manual-verify references only.

Corpora: reuse epic CN SOURCE + JP TARGET from epic_shi_source_target.py
(full homework-length pair). Short excerpts below mirror the prompt few-shot.

Manual verify (UI /api/suggestions — Groq/CF, not Gemini provider):
  1. Paste EPIC_SOURCE_TEXT into 原文, EPIC_TARGET_TEXT into 添削対象.
  2. overallComment: opens with what already works (concepts conveyed),
     then remaining issue categories.
  3. Reasons prefer `現状 → 推奨` (JP forms in 「」, Chinese meta in “”),
     plus accessible why (规范译词 / 语域 / 中式日语 / 活用 etc.).
  4. Dense real-issue coverage across paragraphs; no invented false 缺少.
"""

from .epic_shi_source_target import EPIC_SOURCE_TEXT, EPIC_TARGET_TEXT

# Re-export for convenience in tests / manual paste notes.
QUALITY_BAR_SOURCE_TEXT = EPIC_SOURCE_TEXT
QUALITY_BAR_TARGET_TEXT = EPIC_TARGET_TEXT

# Short pair aligned with backend FEW_SHOT_EXAMPLE.
QUALITY_BAR_SHORT_SOURCE = (
    "现代人阅读史诗的经验，大概是把它们当作一种印在纸上的文字来读。"
    "可实际上，史诗首先是一种声音。"
)
QUALITY_BAR_SHORT_TARGET = (
    "現代人が史詩を読む経験は、史詩を紙に印する文字として読む。"
    "でも、実際には、史詩はまず声である。"
)

# Compliant Gemini-shaped reason: 現状 → 推奨 + accessible why.
# Chinese meta uses “”; Japanese forms use 「」.
QUALITY_BAR_COMPLIANT_REASON = (
    "史詩 → 「叙事詩」（じょじし）：在日语社科/文学翻译中，“史诗”的标准规范"
    "学术译词是「叙事詩」，继续写「史詩」会显得像未消化的中文词形"
)

# Compliant overallComment skeleton: strengths then gaps.
QUALITY_BAR_COMPLIANT_OVERALL = (
    "已能传达“史诗首先是声音、而非只是纸面文字”这一核心对比。"
    "主要问题是规范译词与语域：专名宜用「叙事詩」，论述转折宜用书面语。"
)

# Chinese prose misuse of corner brackets (heuristic MUST flag).
QUALITY_BAR_CN_PROSE_CORNER_MISUSE = "存在「时态」与「语法」问题，需要修改"

QUALITY_BAR_NOTES = (
    "Quality bar is prompt-shaped (Groq/CF/WebLLM). Do not require live LLM "
    "in CI. 「」 only for JP TARGET cites; “” for Chinese meta."
)
