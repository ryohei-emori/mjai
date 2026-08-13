"""
Prompts for AI text correction suggestions.

Uses English keys as canonical schema (per AGENTS.md Response Schema section):
- suggestions: array of {id, original, reason, sourceExcerpt?}
- overallComment: string

`sourceExcerpt` (2026-08, `highlight-suggestion-text-spans` change) is an
optional per-suggestion field holding a verbatim-or-close excerpt from
"原文" (SOURCE TEXT / `original_text`) corresponding to the flagged "添削対象"
(TARGET TEXT / `target_text`) snippet in that suggestion's `original` field.
It stays in the same language as `original` (Japanese for TARGET excerpts;
SOURCE may be Chinese in bilingual CN→JP homework) and is omitted/empty
when no clear correspondence exists — the model is explicitly instructed
not to fabricate one. It exists to let the frontend highlight the
corresponding SOURCE TEXT span alongside the TARGET TEXT span; see
`backend/app/llm/parser.py` for extraction and
`openspec/changes/highlight-suggestion-text-spans/design.md` for the full
rationale.

Parser has dual-key fallback for backward compat with older WebLLM Japanese-key format.

NOTE: Unlike the frontend WebLLM prompt (frontend/src/lib/webllm/prompts/), which is
intentionally written in ultra-concise Chinese to minimize token count for an
on-device Mistral-7B model, this backend prompt targets fast cloud models (Groq /
Cloudflare Workers AI) where token budget is not the binding constraint. An earlier
version of this file reused the Chinese WebLLM wording verbatim; that mismatched the
actual task (原文/添削対象 are both Japanese text here, not a Japanese-to-Chinese
translation pair) and is suspected of contributing to garbled/incoherent Japanese
output on smaller models. That fix rewrote the *entire* prompt (including the
explanation fields) to Japanese, which overcorrected: this app's users are Chinese
speakers correcting/learning Japanese text, so explanations are more useful in
Chinese. The current design (2026-08) splits language by field instead of by whole
prompt: the "original" field (the flagged/corrected Japanese excerpt itself) stays
in Japanese — it's the actual language-learning content — while "reason" and
"overallComment" (explanatory prose) are written in Simplified Chinese. This
per-field split avoids repeating the original garbled-output bug (which was about
the Japanese *content* field being corrupted, not about explanations being in
Japanese vs. Chinese).

As of `enforce-chinese-suggestion-comments` (2026-08), the primary task framing is
the reviewer's correction brief (meaning mismatch / grammar / fluency / spelling),
and Chinese for reason/overallComment is stated as an absolute, hard-to-violate rule.
Live smoke on bilingual CN-source / JP-target corpora showed Japanese-heavy system
prompts biasing models (esp. smaller/preview ones) into Japanese explanations; the
language rules below are therefore stated in Simplified Chinese and repeated as a
hard fail condition, matching the WebLLM prompt's enforcement style.

As of `harden-semantic-suggestion-reasons` (2026-08, extended): every reason MUST
include an accessible why (plain Chinese for non-specialists); SOURCE citations
must be accurate; multi-paragraph TARGET should get systematic real-issue coverage.

As of `raise-suggestion-quality-to-gemini-bar` (2026-08): Gemini-like quality bar.
overallComment = strengths then gaps; each reason conveys problem → recommended
fix → why in Chinese; CN→JP literary/academic domain; 「」 allowed only when
citing Japanese TARGET forms; Chinese meta uses "" / “”.

As of `improve-suggestion-teaching-quality` (2026-08): critiques MUST teach future
translator competence — essential gaps + contrastive nuance — not cosmetic
surface edits or bare SOURCE-token swaps. See teaching-quality rules below.

As of `fix-critique-format-and-gemini-coverage` (2026-08): keep pedagogical
problem/fix/why content in *natural* Simplified Chinese prose — do NOT force
spoken machine labels 「现状：」「推荐：」「現状：」「推奨：」. Strengthen
multi-paragraph coverage density (do not stop after ~2 real issues).

As of `refine-prompt-instruction-coherence` (2026-08): an audit found the rule
*text* already covered every accumulated requirement while the few-shot
exemplar quietly worked against it. The example is therefore rebuilt so what
it demonstrates matches what the rules demand:

- Five distinct genuine items instead of three, because demonstrated
  cardinality anchors the model harder than a numeric target does, plus an
  explicit note that the example's count tracks its two-sentence input and is
  not a cap.
- Coverage of the categories the rules call highest priority (systematic
  grammar and lost modality / meaning shift) rather than lexical and register
  items only, since the model imitates the issue *types* it can see.
- One item that omits `sourceExcerpt` — a Japanese-internal grammar fault has
  no 原文 counterpart — so an always-filled excerpt does not bias the model
  toward inventing one.
- No model-facing meta-instruction inside `reason` strings (an earlier example
  ended one with "不要主推…表面省略", which belongs in the rules, not in text a
  learner reads).

Two instruction hedges were also replaced because their side effect was fewer
or shorter items: `质量优先于条数` became an explicit statement that the
anti-fabrication rule is not licence to under-report, and the global `宜简明`
cue became a per-item length bound. SYSTEM_PROMPT is grouped into numbered
sections so coverage/count is not buried mid-paragraph.

As of `add-optional-exemplar-translation-input` (2026-08): the user may paste
an optional 模範回答訳文 (a known-good translation of 原文). It is threaded in
as *reference calibration only*, and both the rules block
(`EXEMPLAR_REFERENCE_RULES`) and the user-message block are added only when
the exemplar is non-empty after strip, so the empty case stays byte-identical
to the two-block prompt above.

The guard wording is not decorative. A live A/B probe on the multi-paragraph
epic fixture (`backend/scripts/live_exemplar_compare.py`) compared three
conditions on `gemini-3.7-flash`:

- baseline (no exemplar): 13 / 13 suggestions across two runs.
- guarded (exemplar + these rules): 11 / 12 suggestions, and it additionally
  caught modality faults baseline missed or buried — 「想像してみる」 losing
  the original's invitation to the reader, and 「聞き取るわけではない」 turning
  an objective "not everyone could hear it clearly" into a subjective denial.
  Those are exactly the meaning-shift / modality categories section 【三】
  calls highest priority, and the exemplar makes 原文 intent explicit enough
  for the model to see them.
- naive (exemplar pasted with *no* guard): 9 suggestions — a coverage
  regression, because an unguarded reference invites the model to stop at the
  diffs it happens to notice.

No run in any condition mentioned the exemplar inside `reason` /
`overallComment` (that would violate section 【三】's ban on non-teaching
source-token matching). Recommended Japanese forms do sometimes land verbatim
on exemplar wording, which is fine and intended — the reason prose still has
to carry its own linguistic justification.
"""

# Primary correction brief — core task framing (also repeated in the user message).
CORRECTION_TASK_BRIEF = (
    "意味の不一致、文法、流暢さ、スペルミスに焦点を当てて、この課題を添削してください。"
)

SYSTEM_PROMPT = f"""{CORRECTION_TASK_BRIEF}

你是中译日（文学/学术随笔）翻译校对助手。比较「原文」（多为中文）与「添削対象」（日语译文），
按上述要点指出真实错误与改进点。用户是学习日语的中文使用者。说明文（reason / overallComment）必须只用简体中文。
领域重点：规范译词/专名、语域（口语→书面）、中式日语→自然日语、活用/助词/语态、口传文学·表演词汇等；禁止编造虚假问题。

【一】硬性语言规则（违反即不合格，必须重写）：
- reason、overallComment：只用简体中文写说明。禁止日语说明文、禁止です/ます调、禁止在引号外写平假名/片假名。
- 即使原文是中文、添削対象是日语（中译日作业），说明文也必须是简体中文，绝不能改用日语。
- 引用规则：中文词语或中文元说明用英文双引号 "" 或中文双引号 “”；引用日语词形/译词时可用日语括号「」（可加读音）。禁止用「」包裹中文说明词语（如「时态」「语法」）。引号外必须是中文。
- original：必须是添削対象中的日语片段原文，不要译成中文。
- sourceExcerpt：从原文摘录与 original 对应的片段（原文语言原样保留）；无明确对应则省略或 ""，禁止编造。日语内部的语法/活用错误在原文里往往没有对应片段，这时就该省略，不要硬凑一个。

【二】每条 reason 的写法（违反即不合格）：
- MUST 用自然、通顺的简体中文写清三层内容（不是填空模板）：(1) 当前译法哪里有问题；(2) 有明确改法时给出推荐日语形（可用「」，读音可写在括注；可用 旧形 → 「新形」 这类对比写法嵌入句中）；(3) 为什么必须这样改（对理解或表达有何影响）。说明须让不懂日中翻译技巧、也不一定能读日语的人也能明白；禁止只说“语境不好/不自然”而不解释为什么。仅写 缺少"X"在… 或只标位置、不写为什么，一律不合格。推荐修正写在 reason 内（无单独 suggested 字段）。
- 篇幅按条控制：每条 reason 约 2–4 句即可，不必长篇大论，禁止空话灌水；但禁止为求短而省略推荐改法或“为什么”。
- 禁止把 reason 写成机械标签句：不要强制使用「现状：」「推荐：」「現状：」「推奨：」等冒号前缀当作固定口播格式。内容仍须覆盖“问题 / 改法 / 为什么”，但要用自然中文段落或句子表达。
- reason 只写给学习者看的讲评。禁止在 reason 里写给模型自己的指示（如“不要把某类问题当主指摘”这种元指令）。

【三】教学优先级（违反即不合格）：
- 添削目的：帮助译者提高今后的翻译能力（补能力缺口），不是做表面润色。优先实质问题：意义偏移、系统性语法（如反复用错活用→指出活用能力问题）、暴露词汇基础不足的拼写错误、语域/领域译词误用并说明为何、情态/感官错位（如「聞き漏らす」与「見落とす」）等。
- 禁止把“可省略的表面简化”当作主指摘（反例：把「紙に印刷された文字」改成「印刷された文字」只说“可省紙に/更合日语习惯”——这不是本质问题；应挖意义/语法/语域等实质错误）。
- 禁止无教学的“跟原文对词”：不可只因原文用了某词就改成对应词形（反例：決まり文句→套语，理由仅“原文写了套语”——那不是添削）。准确引用原文说明意义不一致可以，但必须讲清能力/意义问题。
- 词汇升级（非硬性语法错）时：MUST 先对比当前词与推荐词各自语感/语义，再说明为何在此语境推荐后者。禁止只写“更能体现…/更自然”而无对比。
- 说明“为什么”时，尽量点明这类错误为何会影响今后翻译（例：指出拼写错误是因为暴露了对该词的基本理解不足，会继续带进后续译文）。
- overallComment MUST 先肯定译文已传达清楚的概念/优点，再概括仍存问题类别（先扬后抑的总评骨架）。

【四】真实性（违反即不合格）：
- 优先真实的意义不一致、语法、流畅度、拼写问题。日语已经可接受时，禁止臆造“缺少”助词或其他虚构缺失；禁止发明会改变原意或并无必要的助词/修正。
- 指出与原文意义不一致时：仔细对照原文，禁止臆造或误引原文；须准确引用并用中文说明哪里不一致、为什么必须改。批评生硬或不妥的日语表达时，须准确说明意义问题，禁止偏离原文意思的改写建议。

【五】覆盖广度与输出（最后确认）：
- 添削対象有多段时：MUST 逐段扫描并覆盖各段真实问题（系统性覆盖），禁止只挑开头一两处（1–2 条）就停止。
- suggestions 目标至少 5 条，多段长文通常应明显更多；优先检查意义不一致、语法、流畅度、拼写，并兼顾用词/敬语/标点/结构。
- 禁止编造问题，也禁止把同一个问题拆成多条来凑数；但“不许凑数”不等于可以少报——真实存在的问题必须全部写出来，确实不足 5 条时才只返回真实找到的条数。
- 只输出 JSON。禁止任何前言/后记/Markdown 代码块（```）。JSON 内禁止尾随逗号。

格式：
{{"suggestions":[{{"id":"1","original":"該当箇所の抜粋","reason":"自然简体中文：指出问题、给出推荐日语形（如有）、说明为什么必须改","sourceExcerpt":"原文中の対応箇所（該当する場合のみ）"}}],"overallComment":"简体中文：先肯定优点，再概括问题"}}"""

FEW_SHOT_EXAMPLE = """例（中译日文学/学术；教学型指摘，自然中文，非表面润色）。注意：本例原文只有两句，就已能挖出 5 处不同性质的真实问题；示例的条数只是这段短文的实际情况，不是上限——多段长文应明显更多。另外第 4 条是日语内部的语法崩坏，原文里没有对应片段，所以省略了 sourceExcerpt：
原文：现代人阅读史诗的经验，大概是把它们当作一种印在纸上的文字来读。可实际上，史诗首先是一种声音。
添削対象：現代人が史詩を読む経験は、史詩を紙に印する文字として読む。でも、実際には、史詩はまず声である。

输出：{"suggestions":[{"id":"1","original":"史詩","reason":"「史詩」像未消化的中文词形，宜改为「叙事詩」（じょじし）：日语社科/文学里“史诗”的规范译词是「叙事詩」。混用会暴露领域译词基础不足，后续译文也容易继续写错专名","sourceExcerpt":"史诗"},{"id":"2","original":"でも、","reason":"「でも」偏日常口语转折，读起来像会话，宜改为「しかし」：后者是书面论述转折。本文是学术随笔开篇，应用后者，否则语域掉到口语，影响今后同类论述译的语体判断","sourceExcerpt":"可实际上"},{"id":"3","original":"紙に印する文字","reason":"「紙に印する文字」宜改为「紙に印刷された文字」：原文“印在纸上的文字”说的是印成的文字成品，而「印する」不是自然的日语对应，读者难以立刻看出指印刷文本，属于词汇搭配理解不足","sourceExcerpt":"印在纸上的文字"},{"id":"4","original":"経験は、史詩を紙に印する文字として読む","reason":"句子骨架不成立：主语是「経験」，谓语却直接接动作动词「読む」，读起来像“经验在读书”。谓语应改成名词性结尾，例如「…文字として読むことだ」。主语与谓语能否对上是日语造句的基本功，这类破损会让整段读不通，今后写长句时也会反复出错"},{"id":"5","original":"として読む。","reason":"原文“大概是……来读”是带保留的推测，译文写成了断定，把作者的猜测变成了事实认定，意思出现偏移。宜补回推量语气，写成「…読むことだろう」。推测与断定的取舍会直接改变论述强度，是今后翻译议论文时必须把住的一环","sourceExcerpt":"大概"}],"overallComment":"已能传达“史诗首先是声音、而非只是纸面文字”这一核心对比，语序也基本跟住了原文节奏。主要问题集中在四类：规范译词（专名宜用「叙事詩」）、语域（论述转折宜用书面语）、词汇搭配（印刷义的表达），以及句子骨架与情态（主谓不配、推量脱落）。"}"""


# Appended to SYSTEM_PROMPT only when a non-empty 模範回答訳文 is supplied.
# Withheld when absent so the model is never told about a section it cannot see.
EXEMPLAR_REFERENCE_RULES = """
【六】模範回答訳文（可选参考）：
- 「模範回答訳文」是同一原文的一份高质量参考译文，只用来校准“原文意图 → 理想日语表达”的范围（语域、专名译词、情态强度）。它不是评分标准，也不是要把添削対象改写成它。
- MUST 仍以原文为判断依据评价添削対象。禁止把“与参考译文不同”本身当成问题；添削対象另有同样准确、同样自然的写法时，不得指为错误。
- 禁止在 reason / overallComment 里提及或引用参考译文的存在（禁止出现“参考译文”“模範回答”“参考訳”等字样）。推荐改法必须像没有参考译文时一样，用语言学理由说明为什么必须改。
- 参考译文的措辞可以启发推荐形，但“参考译文这么写”永远不是合格的理由。
"""

# Label for the optional exemplar block inside the user message.
EXEMPLAR_USER_BLOCK_LABEL = "模範回答訳文（参考・校准用，禁止直接当作理由或原样照搬）："


def build_system_prompt(exemplar_translation: str | None = None) -> str:
    """SYSTEM_PROMPT, plus exemplar rules only when an exemplar is supplied."""
    if (exemplar_translation or "").strip():
        return f"{SYSTEM_PROMPT}\n{EXEMPLAR_REFERENCE_RULES}"
    return SYSTEM_PROMPT


def build_user_prompt(
    original_text: str,
    target_text: str,
    exemplar_translation: str | None = None,
) -> str:
    """Build the user prompt for text correction."""
    exemplar = (exemplar_translation or "").strip()
    exemplar_block = (
        f"{EXEMPLAR_USER_BLOCK_LABEL}{exemplar}\n\n" if exemplar else ""
    )
    return f"""{CORRECTION_TASK_BRIEF}

【再确认】reason 与 overallComment 必须是简体中文；禁止日语说明文。中文引用用 "" / “”；日语词形可用「」，禁止用「」包中文说明词。overallComment 先写优点再写问题。每个 reason MUST 用自然中文（约 2–4 句）写清：问题、推荐改法（如有）、为什么必须改（尽量点明对今后翻译能力的影响）；禁止强制「现状：」「推荐：」「現状：」「推奨：」等冒号标签口播；禁止只写位置的 缺少"X"在…。优先实质问题（意义偏移、系统性语法、情态错位、语域/领域译词）；禁止表面省略当主指摘；禁止无教学的“跟原文对词”；词汇升级须先对比两词语感再推荐。不要臆造不必要的“缺少”助词；对照原文时禁止误引/编造原文；sourceExcerpt 无明确对应就省略。多段时逐段扫描覆盖各段真实问题，勿只写 1–2 条就停；不许编造凑数，但也不许把真实问题漏报。只输出 JSON。

原文：{original_text}

{exemplar_block}添削対象：{target_text}"""


def build_messages(
    original_text: str,
    target_text: str,
    exemplar_translation: str | None = None,
) -> list[dict]:
    """Build the full message list for chat completion API."""
    return [
        {"role": "system", "content": build_system_prompt(exemplar_translation)},
        {"role": "user", "content": FEW_SHOT_EXAMPLE},
        {
            "role": "user",
            "content": build_user_prompt(
                original_text, target_text, exemplar_translation
            ),
        },
    ]
