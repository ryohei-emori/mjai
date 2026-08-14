import {
  CORRECTION_LABEL_MAX_CHARS,
  EMPTY_CORRECTION_LABEL,
  deriveCorrectionLabel,
} from '../correctionLabel'

const label = (targetText?: string | null, originalText?: string | null) =>
  deriveCorrectionLabel({ targetText, originalText })

describe('deriveCorrectionLabel — title-like first line', () => {
  it('uses a short heading line verbatim when body paragraphs follow', () => {
    const result = label('英雄史詩ーいかが宿命に直面\n\n第一段落の本文がここに続く。さらに文章が続く。')
    expect(result).toEqual({ text: '英雄史詩ーいかが宿命に直面', kind: 'title' })
  })

  it('does not append an ellipsis to a title', () => {
    expect(label('無題の詩\n本文です。').text).not.toContain('…')
  })

  it('treats a sentence-terminated short first line as an excerpt, not a title', () => {
    const result = label('以下、訳文です。\n英雄史詩ーいかが宿命に直面')
    expect(result.kind).toBe('excerpt')
    expect(result.text).toBe('以下、訳文です。 英雄史詩ーいかが宿命に直面')
  })

  it('treats a comma-terminated short first line as an excerpt', () => {
    expect(label('まず、\n次の行。').kind).toBe('excerpt')
  })

  it('does not treat a lone short paragraph as a title', () => {
    const result = label('英雄史詩ーいかが宿命に直面')
    expect(result).toEqual({ text: '英雄史詩ーいかが宿命に直面', kind: 'excerpt' })
  })

  it('rejects a first line longer than the label budget as a title', () => {
    const longFirstLine = 'あ'.repeat(CORRECTION_LABEL_MAX_CHARS + 1)
    const result = label(`${longFirstLine}\n次の段落。`)
    expect(result.kind).toBe('excerpt')
    expect(result.text).toBe('あ'.repeat(CORRECTION_LABEL_MAX_CHARS) + '…')
  })

  it('accepts a first line exactly at the budget as a title', () => {
    const atBudget = 'あ'.repeat(CORRECTION_LABEL_MAX_CHARS)
    expect(label(`${atBudget}\n次の段落。`)).toEqual({ text: atBudget, kind: 'title' })
  })
})

describe('deriveCorrectionLabel — excerpts', () => {
  it('shows short single-paragraph text in full with no ellipsis', () => {
    const result = label('短い訳文。')
    expect(result).toEqual({ text: '短い訳文。', kind: 'excerpt' })
  })

  it('truncates long prose at the budget and marks it with an ellipsis', () => {
    const prose = '運命に直面した英雄たちの物語であり、その旅路は長く険しいものであった。'
    const result = label(prose)
    expect(result.kind).toBe('excerpt')
    expect(Array.from(result.text)).toHaveLength(CORRECTION_LABEL_MAX_CHARS + 1)
    expect(result.text.endsWith('…')).toBe(true)
    expect(result.text.slice(0, -1)).toBe(Array.from(prose).slice(0, CORRECTION_LABEL_MAX_CHARS).join(''))
  })

  it('collapses multi-line prose into a single line', () => {
    const result = label('一行目です。\n\n  二行目です。  \n三行目')
    expect(result.text).not.toContain('\n')
    expect(result.text.startsWith('一行目です。 二行目です。 三行目')).toBe(true)
  })

  it('collapses full-width spaces and tabs like any other whitespace', () => {
    expect(label('訳文　です。\tここも').text).toBe('訳文 です。 ここも')
  })

  it('spans past a boilerplate first line so the budget is not wasted', () => {
    const result = label('以下、訳文です。\n運命に直面した英雄たちの長い物語。')
    expect(result.text).toContain('運命に直面した')
  })
})

describe('deriveCorrectionLabel — mixed and multi-byte scripts', () => {
  it('applies the same character budget to mixed Japanese and Chinese text', () => {
    const mixed = '英雄史詩の訳文です。这里是简体中文的说明文字，还要继续写下去才够长。'
    expect(Array.from(mixed).length).toBeGreaterThan(CORRECTION_LABEL_MAX_CHARS)
    const result = label(mixed)
    expect(Array.from(result.text)).toHaveLength(CORRECTION_LABEL_MAX_CHARS + 1)
    expect(result.text.endsWith('…')).toBe(true)
    expect(result.text).toContain('这里是简体中文')
  })

  it('does not split a surrogate pair when truncating', () => {
    // 𠮷 (U+20BB7) is a surrogate pair; the 30th code point lands mid-text.
    const surrogateHeavy = '𠮷'.repeat(40)
    const result = label(surrogateHeavy)
    expect(result.text).toBe('𠮷'.repeat(CORRECTION_LABEL_MAX_CHARS) + '…')
    expect(result.text).not.toContain('\uFFFD')
    expect(result.text.split('\uD842')).toHaveLength(CORRECTION_LABEL_MAX_CHARS + 1)
  })

  it('counts an emoji as one character', () => {
    const withEmoji = '🎭'.repeat(CORRECTION_LABEL_MAX_CHARS)
    expect(label(withEmoji).text).toBe(withEmoji)
  })
})

describe('deriveCorrectionLabel — fallbacks', () => {
  it('falls back to the source text when the target text is blank', () => {
    const result = label('   ', '原文の冒頭がここにある。')
    expect(result).toEqual({ text: '原文の冒頭がここにある。', kind: 'excerpt' })
  })

  it('applies the title rule to the fallback source text too', () => {
    expect(label('', '英雄史詩\n本文。')).toEqual({ text: '英雄史詩', kind: 'title' })
  })

  it('returns the placeholder when both texts are blank', () => {
    expect(label('', '')).toEqual({ text: EMPTY_CORRECTION_LABEL, kind: 'empty' })
    expect(label('  \n\t　\n ')).toEqual({ text: EMPTY_CORRECTION_LABEL, kind: 'empty' })
  })

  it('returns the placeholder for absent and null fields', () => {
    expect(deriveCorrectionLabel({})).toEqual({ text: EMPTY_CORRECTION_LABEL, kind: 'empty' })
    expect(label(null, null)).toEqual({ text: EMPTY_CORRECTION_LABEL, kind: 'empty' })
  })

  it('prefers the target text when both are present', () => {
    expect(label('訳文', '原文').text).toBe('訳文')
  })
})
