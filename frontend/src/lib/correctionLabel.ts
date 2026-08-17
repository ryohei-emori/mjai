/**
 * 添削ラウンドを1行で言い当てる短いラベルの導出ルール
 * （identifiable-history-card-headings change、design.md Decision 1〜3 参照）。
 *
 * Historyカードの見出し・Job Queueカードのプレビュー・TopAppBarベルの通知行が
 * すべてここを使う。以前は後者2つが `targetText.slice(0, 40)` を各々インライン
 * で書いていて、Historyには何もなかった（連番だけ）ため、同じラウンドが
 * パネルによって名前を持ったり持たなかったりしていた。
 *
 * `page.tsx` の `QueuedJob` / `SavedData` を直接importせず構造的な型で受け取る
 * のは、どちらもexportされておらず `"use client"` ページ側（WebLLM / Supabase を
 * 引き込む）に属するため。純関数だけを切り出しておくことでDOMなしで
 * ユニットテストできる（`jobQueue/ordering.ts` と同じ方針）。
 */

/** 訳文も原文も空のときに見出しへ出すプレースホルダ。 */
export const EMPTY_CORRECTION_LABEL = '(empty text)'

/**
 * ラベルに載せる最大文字数（コードポイント単位）。
 *
 * Historyの見出しは `text-body-sm`（14px）でバッジと同じ行を共有するため、
 * これより長くしてもCSSの `truncate` に飲まれて表示されない。タイトル行判定の
 * 上限も同じ値を使い、数字を2つ持たない。
 */
export const CORRECTION_LABEL_MAX_CHARS = 30

/** 省略記号。U+2026 は1文字幅なので30文字の予算をほぼ食わない。 */
const ELLIPSIS = '…'

/**
 * 行末がこれらなら「文/節が続いている」ので見出しではない。短い一文
 * （「以下、訳文です。」など）がタイトルに化けるのを防ぐ。
 */
const SENTENCE_END_PATTERN = /[。．.!！?？…、，,;；:：]$/

export type CorrectionTextSource = {
  targetText?: string | null
  /** 訳文が空のときのフォールバック元。 */
  originalText?: string | null
}

/**
 * `title` = 先頭行をそのまま見出しに採用（省略記号なし）
 * `excerpt` = 本文冒頭を切り出した（予算超過時のみ省略記号つき）
 * `empty` = 訳文・原文ともに空
 */
export type CorrectionLabelKind = 'title' | 'excerpt' | 'empty'

export type CorrectionLabel = {
  text: string
  kind: CorrectionLabelKind
}

/** 連続する空白（改行・全角スペース含む）を単一スペースへ畳む。 */
function collapseWhitespace(text: string): string {
  return text.replace(/\s+/g, ' ').trim()
}

/**
 * コードポイント単位で数えて切る。`slice` はUTF-16コード単位で切るため
 * サロゲートペア（絵文字・CJK拡張漢字）を半分に割って豆腐を出しうる。
 * 併せて、予算の意味が日本語・中国語・ラテン文字で揃う。
 */
function truncateToBudget(text: string): string {
  const chars = Array.from(text)
  if (chars.length <= CORRECTION_LABEL_MAX_CHARS) return text
  return chars.slice(0, CORRECTION_LABEL_MAX_CHARS).join('') + ELLIPSIS
}

/**
 * 短い先頭行が「見出し」と言えるか。
 *
 * 続きの行が存在することを要求するのは、単独の短い段落は「何かの見出し」では
 * なく本文そのものだから。
 */
function isTitleLike(firstLine: string, nonBlankLineCount: number): boolean {
  if (nonBlankLineCount < 2) return false
  if (Array.from(firstLine).length > CORRECTION_LABEL_MAX_CHARS) return false
  return !SENTENCE_END_PATTERN.test(firstLine)
}

/**
 * 添削ラウンドを識別する1行ラベルを返す。訳文が空なら原文へフォールバックし、
 * どちらも空なら `EMPTY_CORRECTION_LABEL`。
 */
export function deriveCorrectionLabel(source: CorrectionTextSource): CorrectionLabel {
  const raw = pickSourceText(source)
  if (raw === null) {
    return { text: EMPTY_CORRECTION_LABEL, kind: 'empty' }
  }

  const lines = raw
    .split(/\r?\n/)
    .map((line) => collapseWhitespace(line))
    .filter((line) => line.length > 0)

  const firstLine = lines[0]
  if (isTitleLike(firstLine, lines.length)) {
    return { text: firstLine, kind: 'title' }
  }

  return { text: truncateToBudget(lines.join(' ')), kind: 'excerpt' }
}

/** 訳文 → 原文の順で、中身のある方を返す。両方空なら null。 */
function pickSourceText(source: CorrectionTextSource): string | null {
  for (const candidate of [source.targetText, source.originalText]) {
    if (typeof candidate === 'string' && candidate.trim().length > 0) return candidate
  }
  return null
}
