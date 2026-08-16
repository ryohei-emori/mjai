"""
Chinese SOURCE + Japanese TARGET pair reported as a critique-quality failure.

Reported (2026-08, `editable-prompt-model-log-and-critique-fix`): on this
passage the cloud critique handed back Chinese words as the corrected form
(改为"对比睡眠数据" / 改为"理论上"), critiqued the Chinese SOURCE instead of the
Japanese TARGET (说原文的"完成"应改为"实现"), proposed interchangeable synonyms
as faults (比較⇄対比, 研究者⇄学者), and proposed a form that does not hold in
Japanese (「睡眠が需要だ」) — while missing the real faults below.

Real faults deliberately kept in TARGET, for the live probe to score:
- 「９点５時間」 — numeral notation; Japanese writes 「9.5時間」/「九時間半」
- 「論理的に言えば」 — means "logically speaking"; the source says 理論上
  (in theory), a meaning shift
- 「データにより」 — repeats 「データ」 from the previous clause where the source
  distinguishes 指標 (metrics) from データ
- 「進化を完成した」 — collocation; Japanese takes 「進化を遂げた」
"""

PRIMATE_SLEEP_SOURCE_TEXT = """多伦多大学的研究者对比了三十种灵长类动物的睡眠数据，根据体型、脑容量等指标推算出：人类理论上需要9.5小时的睡眠，但实际上我们平均只睡7小时左右。研究者认为，人类在演化中把睡眠压缩得更短、更高效，与此同时，文化也完成了逐渐独特的进化。"""

PRIMATE_SLEEP_TARGET_TEXT = """トロント大学の研究者は３０種類の霊長類動物の睡眠データを比較し、体型や脳容量などのデータにより、人類は論理的に言えば９点５時間の睡眠が必要だが、実際には平均で７時間しか寝ていないと計算した。研究者によると、人類は進化の中で睡眠をより短く、より効率的に圧縮し、それと同時に、文化も次第に独特な進化を完成した。"""
