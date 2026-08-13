"use client"

import * as React from "react"
import { cn } from "@/lib/utils"

/**
 * 横スライド（カルーセル）トラック。ジョブキューが縦に無限に伸びて下の
 * パネル（AI Suggestions / History）を押し下げる問題を解決するための
 * プレゼンテーション専用コンポーネント（slide-job-queue-carousel change、
 * design.md Decision 5 参照）。
 *
 * ジョブの状態・確定フロー・永続化については何も知らない。並び替え済みの
 * 配列とカードの描画関数だけを受け取る。
 *
 * スクロールは CSS scroll-snap によるネイティブ実装（Decision 1）。タッチ
 * スワイプ・トラックパッド横スクロール・慣性がブラウザ側から無料で得られ、
 * かつ ~10秒ポーリングで items が入れ替わっても「存在しない index を指す」
 * 事故が起きない。
 */

/**
 * これ未満に縮むとバッジ・時刻・確認ラベルが読めなくなる下限。
 *
 * 右ペインの実測: paneWidth からパネル/カードのpaddingで約84px引かれるため、
 * トラック幅は 280px ペインで約196px、600px（最大）ペインで約516px。230 なら
 * 最大付近で2枚（実幅240px前後）になり、最小幅では1枚に収まる。
 */
const MIN_CARD_WIDTH = 230
/** 右ペインは最大600pxなので、それ以上並べても各カードが狭くなるだけ。 */
const MAX_CARDS_PER_VIEW = 3
/** 「次がある」ことを示すために覗かせる幅（px）。 */
const PEEK_WIDTH = 28
/** ドット表示が走査しづらくなる境界。これを超えたら "N / M" テキストに切り替える。 */
const MAX_INDICATOR_DOTS = 6
/** 端判定の許容誤差（サブピクセル・小数スクロール位置対策）。 */
const EDGE_TOLERANCE = 2

type JobQueueCarouselProps<T> = {
  items: readonly T[]
  getKey: (item: T) => string
  renderItem: (item: T) => React.ReactNode
  /** トラック（スクロール領域）自体のアクセシブル名。 */
  ariaLabel: string
  /** ヘッダー右側に置く追加要素（バッジ等）の前に矢印を差し込む用途向け。 */
  className?: string
}

type ScrollState = {
  canScrollPrev: boolean
  canScrollNext: boolean
  hasOverflow: boolean
  pageCount: number
  activePage: number
}

const INITIAL_SCROLL_STATE: ScrollState = {
  canScrollPrev: false,
  canScrollNext: false,
  hasOverflow: false,
  pageCount: 1,
  activePage: 0,
}

export function JobQueueCarousel<T>({
  items,
  getKey,
  renderItem,
  ariaLabel,
  className,
}: JobQueueCarouselProps<T>) {
  const trackRef = React.useRef<HTMLDivElement | null>(null)
  const [cardsPerView, setCardsPerView] = React.useState(1)
  const [scrollState, setScrollState] = React.useState<ScrollState>(INITIAL_SCROLL_STATE)

  const measure = React.useCallback(() => {
    const track = trackRef.current
    if (!track) return

    const trackWidth = track.clientWidth
    if (trackWidth > 0) {
      const fitted = Math.floor(trackWidth / MIN_CARD_WIDTH)
      setCardsPerView(Math.min(Math.max(fitted, 1), MAX_CARDS_PER_VIEW))
    }

    const maxScroll = track.scrollWidth - trackWidth
    const hasOverflow = maxScroll > EDGE_TOLERANCE
    const pageCount = hasOverflow && trackWidth > 0 ? Math.ceil(track.scrollWidth / trackWidth) : 1

    setScrollState({
      hasOverflow,
      canScrollPrev: hasOverflow && track.scrollLeft > EDGE_TOLERANCE,
      canScrollNext: hasOverflow && track.scrollLeft < maxScroll - EDGE_TOLERANCE,
      pageCount,
      activePage:
        hasOverflow && trackWidth > 0
          ? Math.min(Math.round(track.scrollLeft / trackWidth), pageCount - 1)
          : 0,
    })
  }, [])

  // 幅の実測は右ペインのドラッグリサイズ（メディアクエリでは観測できない）に
  // 追従する必要があるため ResizeObserver で行う。未実装環境（古いSafari /
  // jsdom / SSR）ではカード1枚表示にフォールバックし、クラッシュはさせない。
  React.useEffect(() => {
    measure()
    const track = trackRef.current
    if (!track || typeof ResizeObserver === "undefined") return
    const observer = new ResizeObserver(() => measure())
    observer.observe(track)
    return () => observer.disconnect()
  }, [measure])

  // items が入れ替わったとき（生成完了・ポーリング反映）も端の状態を再評価する。
  React.useEffect(() => {
    measure()
  }, [items, measure])

  const scrollByPage = React.useCallback((direction: -1 | 1) => {
    const track = trackRef.current
    if (!track) return
    track.scrollBy({ left: direction * track.clientWidth, behavior: "smooth" })
  }, [])

  const handleKeyDown = React.useCallback(
    (event: React.KeyboardEvent<HTMLDivElement>) => {
      if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return
      if (!scrollState.hasOverflow) return
      // ページ内には本文テキストエリアや提案コメント編集欄があるため、
      // それらのキャレット移動を奪わない（design.md Decision 6）。
      const target = event.target as HTMLElement | null
      const tag = target?.tagName
      if (tag === "INPUT" || tag === "TEXTAREA" || target?.isContentEditable) return
      event.preventDefault()
      scrollByPage(event.key === "ArrowRight" ? 1 : -1)
    },
    [scrollByPage, scrollState.hasOverflow],
  )

  const { canScrollPrev, canScrollNext, hasOverflow, pageCount, activePage } = scrollState

  // オーバーフローしているときだけ、次カードを覗かせる分を差し引く。
  const cardWidth = hasOverflow
    ? `calc((100% - ${(cardsPerView - 1) * 8 + PEEK_WIDTH}px) / ${cardsPerView})`
    : `calc((100% - ${(cardsPerView - 1) * 8}px) / ${cardsPerView})`

  return (
    <div className={cn("space-y-2", className)}>
      {hasOverflow && (
        <div className="flex items-center justify-between gap-2">
          <p className="text-metadata text-on-surface-variant">
            横スライドで他のジョブを表示
          </p>
          <div className="flex items-center gap-1">
            <button
              type="button"
              aria-label="前のジョブへ"
              disabled={!canScrollPrev}
              onClick={() => scrollByPage(-1)}
              className="p-1 rounded-full text-on-surface-variant hover:bg-surface-container transition-colors disabled:opacity-50 disabled:cursor-default focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-md3-primary"
            >
              <span className="material-symbols-outlined md-20">chevron_left</span>
            </button>
            <button
              type="button"
              aria-label="次のジョブへ"
              disabled={!canScrollNext}
              onClick={() => scrollByPage(1)}
              className="p-1 rounded-full text-on-surface-variant hover:bg-surface-container transition-colors disabled:opacity-50 disabled:cursor-default focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-md3-primary"
            >
              <span className="material-symbols-outlined md-20">chevron_right</span>
            </button>
          </div>
        </div>
      )}

      <div className="relative">
        <div
          ref={trackRef}
          role="group"
          aria-label={ariaLabel}
          tabIndex={0}
          onScroll={measure}
          onKeyDown={handleKeyDown}
          className="job-carousel-track flex gap-2 pb-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-md3-primary rounded-lg"
        >
          {items.map((item) => (
            <div
              key={getKey(item)}
              className="job-carousel-card flex-shrink-0"
              style={{ width: cardWidth }}
            >
              {renderItem(item)}
            </div>
          ))}
        </div>

        {/* 端のフェード: 「その方向にまだ続きがある」ことだけを示す。
            クリックを吸わないよう pointer-events-none。 */}
        {canScrollPrev && (
          <div
            aria-hidden="true"
            className="pointer-events-none absolute left-0 top-0 bottom-2 w-6 bg-gradient-to-r from-surface to-transparent"
          />
        )}
        {canScrollNext && (
          <div
            aria-hidden="true"
            className="pointer-events-none absolute right-0 top-0 bottom-2 w-6 bg-gradient-to-l from-surface to-transparent"
          />
        )}
      </div>

      {pageCount > 1 &&
        (pageCount <= MAX_INDICATOR_DOTS ? (
          <div className="flex items-center justify-center gap-1.5" aria-hidden="true">
            {Array.from({ length: pageCount }, (_, page) => (
              <span
                key={page}
                className={cn(
                  "h-1.5 rounded-full transition-all",
                  page === activePage ? "w-4 bg-md3-primary" : "w-1.5 bg-outline-variant",
                )}
              />
            ))}
          </div>
        ) : (
          <p className="text-metadata text-on-surface-variant text-center" aria-hidden="true">
            {activePage + 1} / {pageCount}
          </p>
        ))}
    </div>
  )
}
