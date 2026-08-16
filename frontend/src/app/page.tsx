"use client"

import { useEffect, useCallback, useRef, useMemo } from "react"
import { useState } from "react"
import Image from "next/image"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"
import { HighlightedTextarea, type TextHighlight } from "@/components/ui/highlighted-textarea"
import { ExemplarTextCard } from "@/components/ui/exemplar-text-card"
import { JobQueueCarousel } from "@/components/ui/job-queue-carousel"
import { PromptSettingsDialog } from "@/components/ui/prompt-settings-dialog"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Checkbox } from "@/components/ui/checkbox"
import { Separator } from "@/components/ui/separator"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Input } from "@/components/ui/input"
import { useToast } from "@/hooks/use-toast"
import {
  sessionAPI,
  historyAPI,
  proposalAPI,
  suggestionsAPI,
  describeSuggestionsFailure,
} from "./api"
import { useAuth } from "./auth-provider"
import { LoginScreen } from "./login-screen"
// Cold path: never statically import `@/lib/webllm` or `@/lib/webllm/engine`
// (those pull `@mlc-ai/web-llm`). Engine loads only via dynamic import below.
import { checkWebGPUSupport } from "@/lib/webllm/webgpu"
import { WEBLLM_MODEL_DISPLAY_NAME, WEBLLM_MODEL_ID } from "@/lib/webllm/config"
import {
  formatElapsedTime,
  formatDownloadProgress,
  PHASE_LABELS,
  getDiagnosticsTracker,
} from "@/lib/webllm/diagnostics"
import { isEngineReady } from "@/lib/webllm/engineReady"
import {
  sortCompletedJobsNewestFirst,
  sortJobsByRelevance,
} from "@/lib/jobQueue/ordering"
import { deriveCorrectionLabel } from "@/lib/correctionLabel"
import {
  dockSessionPaneState,
  isPaneDocked,
  LG_BREAKPOINT_PX,
  loadExemplarCardOpen,
  loadSessionPaneMode,
  saveExemplarCardOpen,
  saveSessionPaneMode,
  toggleSessionPaneState,
  type SessionPaneMode,
  type SessionPaneState,
} from "@/lib/uiPreferences"
import type { EngineStatus } from "@/lib/webllm/types"

/** Lazy-load WebLLM engine only for offline mode or intentional API fallback. */
async function generateWebLLMSuggestions(
  ...args: Parameters<
    typeof import("@/lib/webllm/engine").generateSuggestions
  >
): ReturnType<typeof import("@/lib/webllm/engine").generateSuggestions> {
  const { generateSuggestions } = await import("@/lib/webllm/engine")
  return generateSuggestions(...args)
}

type ActiveNav = 'sessions' | 'dashboard' | 'archive'

// Right pane resizing constants
const RIGHT_PANE_MIN_WIDTH = 280 // px
const RIGHT_PANE_MAX_WIDTH = 600 // px
const RIGHT_PANE_DEFAULT_WIDTH = 448 // 28rem = 448px
const RIGHT_PANE_STORAGE_KEY = 'mjai-right-pane-width'

type CorrectionSuggestion = {
  id: string
  original: string
  reason: string
  selected: boolean
  selectedOrder?: number
  userModifiedReason?: string
  isCustom?: boolean
  // Optional excerpt from SOURCE TEXT (原文) corresponding to `original`
  // (a flagged TARGET TEXT excerpt). Empty/absent when the model found no
  // clear correspondence — used to highlight the matching span in the
  // SOURCE TEXT textarea (see highlight-suggestion-text-spans change).
  sourceExcerpt?: string
}

type SavedData = {
  originalText: string
  instructionPrompt: string
  targetText: string
  aiSuggestions: CorrectionSuggestion[]
  selectedCorrections: CorrectionSuggestion[]
  overallComment: string
  combinedComment: string
  timestamp: Date
  confirmed?: boolean
  historyId?: string
  // Absent for rounds saved before provenance was recorded.
  llmProvider?: string
  llmModel?: string
}

type QueuedJob = {
  id: string
  // ジョブがどのセッションで生成されたか。レビュー中に別セッションへ切り替え
  // られた場合に「実際にこのジョブをレビューしているか」を判定するために
  // 使う（add-suggestion-generation-timer改訂、design.md Decision 7参照）。
  sessionId: string
  targetText: string
  // 生成時の原文。他端末から pending を復元するとき currentSession とズレても使える。
  originalText?: string
  status: 'queued' | 'processing' | 'completed' | 'failed'
  suggestions?: CorrectionSuggestion[]
  overallComment?: string
  error?: string
  queuedAt: Date
  completedAt?: Date
  source?: 'api' | 'webllm'
  // 生成に実際に使われた推論プロバイダ/モデル（source は転送経路の区別）。
  llmProvider?: string
  llmModel?: string
  // 生成成功後に DB へ書いた pending history（確定時は PUT で promote）
  historyId?: string
}

// ユーザーが実際にそのジョブのHITLレビューに向き合っていた時間（＝
// レビュー作業時間）のみを記録する（add-suggestion-generation-timer改訂、
// design.md Decision 7参照）。当初実装（2026-08時点）は「Generate AI
// Suggestions」クリックから「確定してコピー・保存」までの生の経過時間
// （AI処理時間＋キュー待機時間を含む）を計測していたが、最大30件まで
// 並列処理されるキューの性質上、ジョブはユーザーが他の作業をしている間も
// バックグラウンドで待機/処理され続けるため、その値の大半は「ユーザーの
// 作業時間」を表していなかった。現在はジョブキュー経由の確認フロー
// （confirmingJobId）のみが対象な点は変わらず — 実行履歴からの確認
// （confirmingHistoryIndex）には対応する「生成クリック」の開始点が存在
// しないため引き続き対象外（design.md Decision 1参照）。セッション寿命内
// のみのライブUI用の値であり、意図的にlocalStorageへは永続化しない
// （design.md Decision 2参照）。
type JobTimingRecord = {
  jobId: string
  elapsedSeconds: number
  completedAt: Date
}
const MAX_JOB_TIMING_HISTORY = 50

const MAX_CONCURRENT_API_JOBS = 30
const MAX_CONCURRENT_WEBLLM_JOBS = 1

type Session = {
  id: string
  name: string
  createdAt: Date
  correctionCount: number
  originalText: string
  targetText: string
  // 任意の模範回答訳文（原文に対する参考訳）。AIには「対比の参考」としてのみ
  // 渡し、空なら従来どおりプロンプトへ一切含めない。SOURCEと同様に演習単位で
  // 固定なので、生成後にTARGETをクリアするときも消さない。
  exemplarTranslation: string
  suggestions: CorrectionSuggestion[]
  overallComment: string
  savedData: SavedData[]
}

// APIレスポンスの型を定義
type SessionAPIResponse = {
  sessionId: string;
  name: string;
  createdAt: string;
  correctionCount: number;
};

type ProposalAPIResponse = {
  proposalId: string
  originalAfterText: string
  originalReason?: string
  isSelected: boolean
  selectedOrder?: number
  isModified: boolean
  modifiedReason?: string
  isCustom: boolean
}

// --- Draft/JobQueue永続化 (localStorage) ---
// AIのSuggestions(Draft状態)とジョブキューはページ再読み込みで消えるべきではない
// という設計意図に基づき、セッション単位でlocalStorageへ永続化する。
// 参照パターン: RIGHT_PANE_STORAGE_KEY（上部）と同様、try/catchでプライベート
// ブラウジング/クォータ超過時もクラッシュせずメモリのみ動作にフォールバックする。
const DRAFT_STORAGE_PREFIX = 'mjai:draft:'
const JOB_QUEUE_STORAGE_PREFIX = 'mjai:jobQueue:'
const DRAFT_PERSIST_DEBOUNCE_MS = 500

type PersistedDraft = {
  originalText: string
  targetText: string
  exemplarTranslation: string
  suggestions: CorrectionSuggestion[]
  overallComment: string
  confirmingHistoryIndex: number | null
  confirmingJobId: string | null
}

type PersistedQueuedJob = Omit<QueuedJob, 'queuedAt' | 'completedAt'> & {
  queuedAt: string
  completedAt?: string
}

function loadDraftFromStorage(sessionId: string): PersistedDraft | null {
  if (typeof window === 'undefined') return null
  try {
    const raw = window.localStorage.getItem(`${DRAFT_STORAGE_PREFIX}${sessionId}`)
    if (!raw) return null
    const parsed = JSON.parse(raw) as Partial<PersistedDraft>
    return {
      originalText: parsed.originalText || '',
      targetText: parsed.targetText || '',
      // このフィールド追加前に永続化されたDraftにはキーが無いため空文字で補う
      exemplarTranslation: parsed.exemplarTranslation || '',
      suggestions: Array.isArray(parsed.suggestions) ? parsed.suggestions : [],
      overallComment: parsed.overallComment || '',
      confirmingHistoryIndex:
        typeof parsed.confirmingHistoryIndex === 'number' ? parsed.confirmingHistoryIndex : null,
      confirmingJobId: parsed.confirmingJobId || null,
    }
  } catch (error) {
    console.warn('[persistence] Failed to load draft from localStorage:', error)
    return null
  }
}

function saveDraftToStorage(sessionId: string, draft: PersistedDraft) {
  if (typeof window === 'undefined') return
  try {
    const key = `${DRAFT_STORAGE_PREFIX}${sessionId}`
    const isEmpty =
      !draft.originalText &&
      !draft.targetText &&
      !draft.exemplarTranslation &&
      draft.suggestions.length === 0 &&
      !draft.overallComment &&
      draft.confirmingHistoryIndex === null &&
      !draft.confirmingJobId
    if (isEmpty) {
      // Draftが何も無ければ空エントリを残さずキーごと削除する
      window.localStorage.removeItem(key)
      return
    }
    window.localStorage.setItem(key, JSON.stringify(draft))
  } catch (error) {
    console.warn('[persistence] Failed to save draft to localStorage:', error)
  }
}

function clearDraftFromStorage(sessionId: string) {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.removeItem(`${DRAFT_STORAGE_PREFIX}${sessionId}`)
  } catch (error) {
    console.warn('[persistence] Failed to clear draft from localStorage:', error)
  }
}

function loadJobQueueFromStorage(sessionId: string): QueuedJob[] {
  if (typeof window === 'undefined') return []
  try {
    const raw = window.localStorage.getItem(`${JOB_QUEUE_STORAGE_PREFIX}${sessionId}`)
    if (!raw) return []
    const parsed = JSON.parse(raw) as PersistedQueuedJob[]
    if (!Array.isArray(parsed)) return []
    return parsed.map((job) => ({
      ...job,
      // sessionIdフィールド追加（add-suggestion-generation-timer改訂）前に
      // 永続化された既存データにはこのフィールドが無いため、読み込み元の
      // sessionIdをフォールバックとして補う
      sessionId: job.sessionId || sessionId,
      // 再読み込み時点で「処理中」だったジョブはネットワーク要求を再開できない
      // ため、キュー消化useEffectが再取得できるようqueuedへ戻す（ジョブを
      // サイレントに失うことはしない）
      status: job.status === 'processing' ? 'queued' : job.status,
      queuedAt: new Date(job.queuedAt),
      completedAt: job.completedAt ? new Date(job.completedAt) : undefined,
    }))
  } catch (error) {
    console.warn('[persistence] Failed to load job queue from localStorage:', error)
    return []
  }
}

function saveJobQueueToStorage(sessionId: string, jobs: QueuedJob[]) {
  if (typeof window === 'undefined') return
  try {
    const key = `${JOB_QUEUE_STORAGE_PREFIX}${sessionId}`
    if (jobs.length === 0) {
      window.localStorage.removeItem(key)
      return
    }
    const serializable: PersistedQueuedJob[] = jobs.map((job) => ({
      ...job,
      queuedAt: job.queuedAt.toISOString(),
      completedAt: job.completedAt ? job.completedAt.toISOString() : undefined,
    }))
    window.localStorage.setItem(key, JSON.stringify(serializable))
  } catch (error) {
    console.warn('[persistence] Failed to save job queue to localStorage:', error)
  }
}

function clearJobQueueFromStorage(sessionId: string) {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.removeItem(`${JOB_QUEUE_STORAGE_PREFIX}${sessionId}`)
  } catch (error) {
    console.warn('[persistence] Failed to clear job queue from localStorage:', error)
  }
}

/**
 * AI Diagnostics Panel Component
 * Displays detailed phase, timing, and progress information during AI inference
 */
function AIDiagnosticsPanel({ status }: { status: EngineStatus }) {
  const diagnostics = status.diagnostics
  
  // Determine background color based on state
  const bgClass = status.state === "error" 
    ? "bg-red-50 border-red-200" 
    : "bg-primary-container border-md3-primary/30"
  const textClass = status.state === "error"
    ? "text-red-800"
    : "text-on-primary-container"
  const textMutedClass = status.state === "error"
    ? "text-red-700"
    : "text-on-primary-container/70"
  const progressBgClass = status.state === "error"
    ? "bg-red-200"
    : "bg-md3-primary/20"
  const progressFgClass = status.state === "error"
    ? "bg-red-600"
    : "bg-md3-primary"

  return (
    <div className={`p-3 border rounded-lg ${bgClass}`}>
      {/* Header: Model info + current phase */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className={`material-symbols-outlined md-18 animate-spin ${textClass}`}>progress_activity</span>
          <span className={`text-body-sm font-medium ${textClass}`}>
            {diagnostics?.phaseLabel || (status.state === "loading" ? "準備中" : status.state === "generating" ? "分析中" : "処理中")}
          </span>
        </div>
        <div className="flex items-center gap-2 text-metadata">
          <span className={`font-mono ${textMutedClass}`}>
            {WEBLLM_MODEL_DISPLAY_NAME}
          </span>
        </div>
      </div>
      
      {/* Progress bar for model download */}
      {status.state === "loading" && (
        <>
          <div className={`w-full ${progressBgClass} rounded-full h-2 mb-1`}>
            <div 
              className={`${progressFgClass} h-2 rounded-full transition-all duration-300`}
              style={{ width: `${Math.round(status.progress * 100)}%` }}
            />
          </div>
          <p className={`text-metadata ${textMutedClass}`}>
            {status.text || formatDownloadProgress(status.progress)}
          </p>
        </>
      )}
      
      {/* Timing info */}
      {diagnostics && (
        <div className={`flex gap-4 text-metadata ${textMutedClass} mt-2`}>
          <span>
            現在フェーズ: {formatElapsedTime(diagnostics.currentPhaseElapsedMs)}
          </span>
          <span>
            合計: {formatElapsedTime(diagnostics.totalElapsedMs)}
          </span>
        </div>
      )}
      
      {/* Timeout info - shown instead of generic error for timeout cases */}
      {diagnostics?.timeoutPhase && (
        <div className="mt-2 p-2 bg-red-100 rounded text-metadata text-red-800">
          <strong>タイムアウト:</strong> {PHASE_LABELS[diagnostics.timeoutPhase]} フェーズでタイムアウトしました
        </div>
      )}
      
      {/* Error message - only show if NOT a timeout (timeoutPhase already shows the info) */}
      {status.state === "error" && !diagnostics?.timeoutPhase && (
        <div className="mt-2 p-2 bg-red-100 rounded text-metadata text-red-800">
          <strong>エラー:</strong> {"error" in status ? status.error : "不明なエラー"}
        </div>
      )}
      
      {/* DevTools hint (only in development) */}
      {process.env.NODE_ENV === "development" && (
        <p className={`text-metadata ${textMutedClass} mt-2 opacity-60`}>
          DevTools: window.__webllmDiagnostics.getState()
        </p>
      )}
    </div>
  )
}

export default function TextCorrectionApp() {
  const { session, isLoading: isAuthLoading, signOut, user } = useAuth()
  const [sessions, setSessions] = useState<Session[]>([])
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  // SSR安全な初期値。実際の保存済み設定はマウント後のeffectで反映する。
  const [sessionPaneMode, setSessionPaneMode] = useState<SessionPaneMode>('floating')
  const [isExemplarCardOpen, setIsExemplarCardOpen] = useState(false)
  const [customCorrection, setCustomCorrection] = useState({ original: "", reason: "" })
  const [showCustomForm, setShowCustomForm] = useState(false)
  const [selectionCounter, setSelectionCounter] = useState(0)
  const [webllmStatus, setWebllmStatus] = useState<EngineStatus>({ state: "idle" })
  const [webgpuSupported, setWebgpuSupported] = useState<boolean | null>(null)
  const [webgpuUnsupportedReason, setWebgpuUnsupportedReason] = useState<string | null>(null)
  const [offlineMode, setOfflineMode] = useState(false)
  const [lastSuggestionSource, setLastSuggestionSource] = useState<"api" | "webllm" | null>(null)
  // Which model produced the suggestions currently on screen (cloud model id or
  // the WebLLM model), shown as an unobtrusive caption. null = unknown, e.g. a
  // History round saved before provenance was recorded.
  const [lastSuggestionModel, setLastSuggestionModel] = useState<string | null>(null)
  const [promptSettingsOpen, setPromptSettingsOpen] = useState(false)
  const [jobQueue, setJobQueue] = useState<QueuedJob[]>([])
  // 「確定してコピー・保存」の二重送信を防止し、1生成ラウンドにつき
  // 添削データ(History)エントリが1件だけ作成されることを保証する
  const [isSaving, setIsSaving] = useState(false)
  const [confirmingHistoryIndex, setConfirmingHistoryIndex] = useState<number | null>(null)
  const [activeNav, setActiveNav] = useState<ActiveNav>('sessions')
  const [bellShake, setBellShake] = useState(false)
  const [bellPanelOpen, setBellPanelOpen] = useState(false)
  const [sessionSearch, setSessionSearch] = useState("")
  const [rightPaneWidth, setRightPaneWidth] = useState(RIGHT_PANE_DEFAULT_WIDTH)
  const [isResizing, setIsResizing] = useState(false)
  const [isLgScreen, setIsLgScreen] = useState(false)
  // Hover-preview trigger for suggestion-card text-span highlighting
  // (see highlight-suggestion-text-spans design.md Decision 2).
  const [hoveredSuggestionId, setHoveredSuggestionId] = useState<string | null>(null)
  // ジョブごとの「レビュー作業時間」履歴（最新表示・平均算出用、
  // add-suggestion-generation-timer改訂、design.md Decision 7）。
  const [jobTimingHistory, setJobTimingHistory] = useState<JobTimingRecord[]>([])
  // レビューセグメントのライブ表示を1秒ごとに更新するための現在時刻tick
  const [nowTick, setNowTick] = useState<number>(() => Date.now())
  // タブが可視状態かどうか（Page Visibility API）。非表示の間はレビュー
  // セグメントの計測を一時停止する（add-suggestion-generation-timer改訂、
  // design.md Decision 7）。
  const [isTabVisible, setIsTabVisible] = useState<boolean>(() =>
    typeof document === 'undefined' ? true : document.visibilityState === 'visible',
  )
  // ジョブごとに「クローズ済みレビューセグメント」の累計ミリ秒を保持する。
  // ref管理のため更新は再レンダーを起こさない（ライブ表示はnowTickが駆動する）。
  const reviewAccumulatedMsRef = useRef<Map<string, number>>(new Map())
  // 現在オープン中のレビューセグメントの開始時刻（ミリ秒epoch）をジョブIDごとに
  // 保持する。オープン中のジョブは高々1件を想定するが、Mapで安全に扱う。
  const reviewSegmentStartRef = useRef<Map<string, number>>(new Map())
  const bellShakeTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const bellPanelRef = useRef<HTMLDivElement | null>(null)
  const resizeRef = useRef<{ startX: number; startWidth: number } | null>(null)
  // このブラウザタブのセッションでDraft/ジョブキューを既に復元済みのセッションID
  // （同一セッションへ何度も切り替えるたびに復元し直してユーザーの最新編集を
  // 巻き戻してしまうことを防ぐ）
  const restoredDraftSessionIdsRef = useRef<Set<string>>(new Set())
  const draftSaveTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const jobQueueSaveTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  // loadSessionDetails は confirmingJobId state より前に定義されるため、
  // アクティブなレビュー上書き防止はこの ref 経由で読む。
  const confirmingJobIdRef = useRef<string | null>(null)
  const { toast } = useToast()

  // Load persisted right pane width and detect screen size on mount
  useEffect(() => {
    if (typeof window !== 'undefined') {
      // Load saved width
      const saved = localStorage.getItem(RIGHT_PANE_STORAGE_KEY)
      if (saved) {
        const width = parseInt(saved, 10)
        if (!isNaN(width) && width >= RIGHT_PANE_MIN_WIDTH && width <= RIGHT_PANE_MAX_WIDTH) {
          setRightPaneWidth(width)
        }
      }

      setSessionPaneMode(loadSessionPaneMode())
      setIsExemplarCardOpen(loadExemplarCardOpen())

      // Detect screen size
      const checkScreenSize = () => setIsLgScreen(window.innerWidth >= LG_BREAKPOINT_PX)
      checkScreenSize()
      window.addEventListener('resize', checkScreenSize)
      return () => window.removeEventListener('resize', checkScreenSize)
    }
  }, [])

  // 実効的な提示形態。狭い画面へリサイズしても保存済みの `docked` 設定は
  // 上書きせず、広げ直せばドッキング表示に戻る。
  const isSessionPaneDocked = isPaneDocked(
    { mode: sessionPaneMode, overlayOpen: sidebarOpen },
    isLgScreen,
  )

  // 遷移そのものは uiPreferences 側の純粋関数が持つ（テスト可能にするため）。
  // ここではその結果を state と localStorage へ反映するだけ。
  const applySessionPaneState = useCallback((next: SessionPaneState) => {
    setSessionPaneMode((prev) => {
      if (prev !== next.mode) saveSessionPaneMode(next.mode)
      return next.mode
    })
    setSidebarOpen(next.overlayOpen)
  }, [])

  const toggleSessionPane = useCallback(() => {
    applySessionPaneState(
      toggleSessionPaneState({ mode: sessionPaneMode, overlayOpen: sidebarOpen }, isLgScreen),
    )
  }, [applySessionPaneState, sessionPaneMode, sidebarOpen, isLgScreen])

  const dockSessionPane = useCallback(() => {
    applySessionPaneState(dockSessionPaneState())
  }, [applySessionPaneState])

  const handleExemplarCardOpenChange = useCallback((open: boolean) => {
    setIsExemplarCardOpen(open)
    saveExemplarCardOpen(open)
  }, [])

  // Right pane resize handlers
  const handleResizeStart = useCallback((e: React.PointerEvent) => {
    e.preventDefault()
    setIsResizing(true)
    resizeRef.current = { startX: e.clientX, startWidth: rightPaneWidth }
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
  }, [rightPaneWidth])

  useEffect(() => {
    if (!isResizing) return

    const handlePointerMove = (e: PointerEvent) => {
      if (!resizeRef.current) return
      const deltaX = resizeRef.current.startX - e.clientX
      const newWidth = Math.min(
        RIGHT_PANE_MAX_WIDTH,
        Math.max(RIGHT_PANE_MIN_WIDTH, resizeRef.current.startWidth + deltaX)
      )
      setRightPaneWidth(newWidth)
    }

    const handlePointerUp = () => {
      setIsResizing(false)
      resizeRef.current = null
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
      // Persist to localStorage
      localStorage.setItem(RIGHT_PANE_STORAGE_KEY, rightPaneWidth.toString())
    }

    window.addEventListener('pointermove', handlePointerMove)
    window.addEventListener('pointerup', handlePointerUp)

    return () => {
      window.removeEventListener('pointermove', handlePointerMove)
      window.removeEventListener('pointerup', handlePointerUp)
    }
  }, [isResizing, rightPaneWidth])

  // Close notification panel on outside click or Escape
  useEffect(() => {
    if (!bellPanelOpen) return

    const handlePointerDown = (event: MouseEvent | PointerEvent) => {
      const target = event.target as Node | null
      if (target && bellPanelRef.current && !bellPanelRef.current.contains(target)) {
        setBellPanelOpen(false)
      }
    }
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setBellPanelOpen(false)
      }
    }

    document.addEventListener('pointerdown', handlePointerDown)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('pointerdown', handlePointerDown)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [bellPanelOpen])

  // Get user avatar from Google OAuth metadata
  const avatarUrl = user?.user_metadata?.avatar_url || user?.user_metadata?.picture

  // Derived state - must be declared before any hooks that reference it
  const currentSession = sessions.find((s) => s.id === currentSessionId)

  // Check WebGPU support on mount
  useEffect(() => {
    const check = checkWebGPUSupport()
    setWebgpuSupported(check.supported)
    if (!check.supported) {
      setWebgpuUnsupportedReason(check.reason || "WebGPU is not supported")
    }
  }, [])

  // Periodic timer updates during WebLLM processing
  // This fixes the "0ms" display bug by polling the tracker for fresh timing data
  useEffect(() => {
    // Only update when in active WebLLM processing states
    const activeStates = ["loading", "generating", "checking_webgpu"]
    if (!activeStates.includes(webllmStatus.state)) return

    const intervalId = setInterval(() => {
      const tracker = getDiagnosticsTracker()
      const freshDiagnostics = tracker.getState()
      
      // Update the status with fresh timing data while preserving other status properties
      setWebllmStatus(prev => ({
        ...prev,
        diagnostics: freshDiagnostics,
      }))
    }, 100) // Update every 100ms for smooth timer display

    return () => clearInterval(intervalId)
  }, [webllmStatus.state])

  // タブの可視状態を監視する（Page Visibility API）。非表示化した瞬間に
  // 進行中のレビューセグメントを一時停止できるよう、isTabVisibleへ反映する
  // （add-suggestion-generation-timer改訂、design.md Decision 7）。
  // ライブ更新用のticking effectとレビューセグメントのopen/close effectは
  // confirmingJobId宣言（後述）に依存するため、そちらの近くにまとめて配置する。
  useEffect(() => {
    const handleVisibilityChange = () => setIsTabVisible(document.visibilityState === 'visible')
    document.addEventListener('visibilitychange', handleVisibilityChange)
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange)
  }, [])

  // 単一ジョブを非同期処理する関数（並列実行可能）
  // exemplarTranslation は任意。空文字なら api.ts / WebLLM prompt 側でキーごと
  // 省略され、プロンプトは従来と完全に同一になる（後方互換）。
  const processJobAsync = useCallback(async (jobId: string, targetText: string, originalText: string, exemplarTranslation: string = "") => {
    let sessionIdForPersist = ''
    // ジョブをprocessingに更新しつつ sessionId を確保（DB pending 永続化用）
    setJobQueue((prev) =>
      prev.map((j) => {
        if (j.id !== jobId) return j
        sessionIdForPersist = j.sessionId
        return { ...j, status: 'processing' as const, originalText }
      }),
    )

    toast({
      title: "処理開始",
      description: `ジョブ ${jobId.slice(-4)} を処理中...`,
    })

    try {
      let suggestions: CorrectionSuggestion[] = []
      let overallComment = ''
      let source: 'api' | 'webllm' = 'api'
      let llmProvider: string | undefined
      let llmModel: string | undefined

      if (offlineMode) {
        // WebLLM ONLY when オフラインモード is explicitly ON (no API auto-fallback).
        source = 'webllm'
        if (!webgpuSupported) {
          throw new Error(webgpuUnsupportedReason || "WebGPU非対応")
        }

        const data = await generateWebLLMSuggestions(
          { originalText, targetText, exemplarTranslation, instructionPrompt: "CCTalkからの添削指示" },
          (status) => setWebllmStatus(status)
        )
        suggestions = data.suggestions.map(s => ({ ...s, selected: false }))
        overallComment = data.overallComment
        llmProvider = 'webllm'
        llmModel = WEBLLM_MODEL_ID
      } else {
        // Cloud API only — failures surface as failed jobs; never call WebLLM.
        try {
          const data = await suggestionsAPI.generate(originalText, targetText, exemplarTranslation)
          console.log("[processJobAsync] API response received:", {
            suggestionsCount: data.suggestions?.length ?? 0,
            suggestions: data.suggestions,
            overallComment: data.overallComment?.substring(0, 100),
          })
          suggestions = data.suggestions.map(s => ({ ...s, selected: false }))
          overallComment = data.overallComment
          source = 'api'
          llmProvider = data.llmProvider || undefined
          llmModel = data.llmModel || undefined
        } catch (apiError) {
          // Localized message plus the per-provider breakdown: a generic
          // failure line cannot tell an unset key from an exhausted quota from
          // a timeout, and only the user can see this screen.
          console.warn("[suggestions] API failed (no WebLLM fallback):", apiError)
          throw new Error(describeSuggestionsFailure(apiError))
        }
      }

      // ジョブを完了に更新（DB 永続化は続けて行い historyId を後付け）
      setJobQueue(prev => prev.map(j => 
        j.id === jobId 
          ? { 
              ...j, 
              status: 'completed' as const, 
              suggestions,
              overallComment,
              source,
              llmProvider,
              llmModel,
              originalText,
              completedAt: new Date() 
            } 
          : j
      ))

      setLastSuggestionSource(source)
      setLastSuggestionModel(llmModel ?? null)

      // Trigger bell shake animation on job completion
      setBellShake(true)
      if (bellShakeTimeoutRef.current) {
        clearTimeout(bellShakeTimeoutRef.current)
      }
      bellShakeTimeoutRef.current = setTimeout(() => {
        setBellShake(false)
      }, 600)

      toast({
        title: "完了",
        description: `ジョブ ${jobId.slice(-4)} が完了しました`,
      })

      // Shared DB: persist pending history + proposals so other envs can see them
      if (sessionIdForPersist) {
        try {
          const savedHistory = await historyAPI.createHistory({
            sessionId: sessionIdForPersist,
            originalText,
            targetText,
            instructionPrompt: "CCTalkからの添削指示",
            combinedComment: overallComment,
            overallComment,
            status: "pending",
            provider: source,
            ...(llmProvider ? { llmProvider } : {}),
            ...(llmModel ? { llmModel } : {}),
            clientJobId: jobId,
          })
          if (!savedHistory?.historyId) {
            throw new Error("pending historyId missing")
          }
          const persistedSuggestions: CorrectionSuggestion[] = []
          for (const suggestion of suggestions) {
            const created = await proposalAPI.createProposal({
              historyId: savedHistory.historyId,
              type: "AI",
              originalAfterText: suggestion.original,
              originalReason: suggestion.reason,
              modifiedAfterText: suggestion.original,
              modifiedReason: suggestion.reason,
              isSelected: false,
              isModified: false,
              isCustom: false,
            })
            persistedSuggestions.push({
              ...suggestion,
              id: created.proposalId || suggestion.id,
              selected: false,
            })
          }
          setJobQueue((prev) =>
            prev.map((j) =>
              j.id === jobId
                ? {
                    ...j,
                    historyId: savedHistory.historyId,
                    suggestions: persistedSuggestions,
                  }
                : j,
            ),
          )
        } catch (persistError) {
          console.error("[processJobAsync] Failed to persist pending suggestions:", persistError)
          toast({
            title: "DB同期失敗",
            description:
              "提案は表示されていますが、共有DBへの保存に失敗しました。この端末のジョブは残っています。",
            variant: "destructive",
          })
        }
      }

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "不明なエラー"
      
      setJobQueue(prev => prev.map(j => 
        j.id === jobId 
          ? { ...j, status: 'failed' as const, error: errorMessage, completedAt: new Date() } 
          : j
      ))

      toast({
        title: "エラー",
        description: `ジョブ ${jobId.slice(-4)}: ${errorMessage}`,
        variant: "destructive",
      })
    }
  }, [offlineMode, webgpuSupported, webgpuUnsupportedReason, toast])

  // ジョブをキューに追加し、並列処理を開始する関数
  const addJobAndProcess = useCallback((targetText: string) => {
    if (!currentSession) return false

    // 原文テキストが未入力の場合、API呼び出し（originalText/targetText必須）が
    // 400エラーになるため、事前にガードする
    if (!currentSession.originalText.trim()) {
      toast({
        title: "原文テキストが未入力です",
        description: "AI提案を生成する前に「原文テキスト」を入力してください。",
        variant: "destructive",
      })
      return false
    }
    
    const MAX_QUEUE_SIZE = 10
    const currentQueueSize = jobQueue.filter(j => j.status === 'queued' || j.status === 'processing').length
    
    if (currentQueueSize >= MAX_QUEUE_SIZE) {
      toast({
        title: "キュー上限",
        description: `キューの上限（${MAX_QUEUE_SIZE}件）に達しています。処理完了後に追加してください。`,
        variant: "destructive",
      })
      return false
    }

    const newJob: QueuedJob = {
      id: `job-${Date.now()}`,
      sessionId: currentSession.id,
      targetText,
      originalText: currentSession.originalText,
      status: 'queued',
      queuedAt: new Date(),
    }
    
    setJobQueue(prev => [...prev, newJob])
    
    // 即座にジョブ処理を開始（並列処理対応）
    const processingCount = jobQueue.filter(j => j.status === 'processing').length
    const maxConcurrent = offlineMode ? MAX_CONCURRENT_WEBLLM_JOBS : MAX_CONCURRENT_API_JOBS
    
    if (processingCount < maxConcurrent) {
      // スロットが空いているので即座に処理開始
      processJobAsync(
        newJob.id,
        targetText,
        currentSession.originalText,
        currentSession.exemplarTranslation,
      )
    }
    
    toast({
      title: "キューに追加",
      description: `ジョブをキューに追加しました`,
    })
    
    return true
  }, [jobQueue, currentSession, offlineMode, processJobAsync, toast])

  // 失敗したジョブを再試行する関数（ジョブキュー/実行履歴から直接呼び出し可能）
  // 既存のaddJobAndProcess/processJobAsyncパスをそのまま再利用し、
  // 同一のターゲットテキストで新しいジョブを開始する（重複ロジックを避ける）
  const retryJob = useCallback((job: QueuedJob) => {
    setJobQueue(prev => prev.filter(j => j.id !== job.id))
    addJobAndProcess(job.targetText)
  }, [addJobAndProcess])

  // キュー消化ループ - 空きスロットがあればqueuedジョブをprocessingに移行
  useEffect(() => {
    if (!currentSession) return
    
    const processingCount = jobQueue.filter(j => j.status === 'processing').length
    const maxConcurrent = offlineMode ? MAX_CONCURRENT_WEBLLM_JOBS : MAX_CONCURRENT_API_JOBS
    const availableSlots = maxConcurrent - processingCount
    
    if (availableSlots <= 0) return
    
    // 次に処理すべきqueuedジョブを取得
    const queuedJobs = jobQueue.filter(j => j.status === 'queued')
    const jobsToStart = queuedJobs.slice(0, availableSlots)
    
    // 各ジョブを並列で処理開始
    jobsToStart.forEach(job => {
      processJobAsync(
        job.id,
        job.targetText,
        currentSession.originalText,
        currentSession.exemplarTranslation,
      )
    })
  }, [jobQueue, currentSession, offlineMode, processJobAsync])

  // セッション更新をAPIに実行（TDZ回避のため、handleGenerateClick/confirmJobより前に定義）
  const updateCurrentSession = useCallback((updates: Partial<Session>) => {
    if (!currentSessionId) return
    setSessions((prev) =>
      prev.map((session) => (session.id === currentSessionId ? { ...session, ...updates } : session)),
    )
  }, [currentSessionId])

  // ボタンクリックハンドラー - 常にキューに追加して処理開始
  //
  // 注意（persist-source-target-text-input変更で調査・明文化）: 下記の
  // targetText: "" クリアは「1つの固定SOURCEに対して複数のTARGETを連続投入する」
  // ワークフローのための意図的な仕様であり、バグではない。addJobAndProcess()が
  // 同期的にジョブをキュー（jobQueue、独立してlocalStorageへ永続化される）へ
  // 積んだ後にのみクリアが実行されるため、投入されたテキストがキューに載らずに
  // 消失するタイミングウィンドウは存在しない。SOURCE（originalText）はこの
  // ハンドラーが一切変更しない。
  const handleGenerateClick = useCallback(() => {
    if (!currentSession?.targetText.trim()) return
    
    addJobAndProcess(currentSession.targetText)
    // テキストエリアをクリアして次の入力を待つ
    updateCurrentSession({ targetText: "" })
  }, [currentSession, addJobAndProcess, updateCurrentSession])

  // セッション詳細をオンデマンドで取得（共有DB上の histories + ai_proposals）。
  // confirmed → History、pending → Job Queue へマージ（他端末/他環境の未確定提案を可視化）。
  const loadSessionDetails = useCallback(async (sessionId: string) => {
    try {
      console.log("Loading session details for:", sessionId)
      const historiesData = await historyAPI.getHistories(sessionId)
      console.log("Histories for session", sessionId, ":", historiesData)

      const serverSaved: SavedData[] = []
      const pendingJobs: QueuedJob[] = []

      for (const history of historiesData) {
        const proposalsData: ProposalAPIResponse[] = await proposalAPI.getProposals(history.historyId)
        const aiSuggestions: CorrectionSuggestion[] = proposalsData.map((proposal) => ({
          id: proposal.proposalId,
          original: proposal.originalAfterText,
          reason: proposal.originalReason || "",
          // API(Postgres BOOLEAN列)はJSONの true/false を返す。
          // 以前は `=== 1` で比較しており常にfalseになっていた。
          selected: !!proposal.isSelected,
          selectedOrder: proposal.selectedOrder,
          userModifiedReason: proposal.modifiedReason,
          isCustom: !!proposal.isCustom,
        }))

        const status = history.status || "confirmed"
        const overall =
          history.overallComment || history.combinedComment || ""
        const ts = history.timestamp ? new Date(history.timestamp) : new Date()

        if (status === "pending" || status === "failed") {
          pendingJobs.push({
            id: history.clientJobId || `history-${history.historyId}`,
            sessionId,
            targetText: history.targetText || "",
            originalText: history.originalText,
            status: status === "failed" ? "failed" : "completed",
            suggestions: status === "failed" ? undefined : aiSuggestions,
            overallComment: overall,
            error: status === "failed" ? overall || "生成に失敗しました" : undefined,
            queuedAt: ts,
            completedAt: ts,
            source: history.provider === "webllm" ? "webllm" : "api",
            llmProvider: history.llmProvider || undefined,
            llmModel: history.llmModel || undefined,
            historyId: history.historyId,
          })
          continue
        }

        serverSaved.push({
          originalText: history.originalText,
          instructionPrompt: history.instructionPrompt || "",
          targetText: history.targetText,
          aiSuggestions,
          selectedCorrections: aiSuggestions.filter((s) => s.selected),
          overallComment: overall,
          combinedComment: history.combinedComment || overall,
          timestamp: ts,
          confirmed: true,
          historyId: history.historyId,
          llmProvider: history.llmProvider || undefined,
          llmModel: history.llmModel || undefined,
        })
      }

      setSessions((prevSessions) =>
        prevSessions.map((s) => {
          if (s.id !== sessionId) return s
          // Keep optimistic local History rows that do not yet have historyId
          // (background save in flight after confirm-copy).
          const pendingLocal = (s.savedData || []).filter((d) => !d.historyId)
          const stillPending = pendingLocal.filter((local) => {
            return !serverSaved.some(
              (srv) =>
                srv.combinedComment === local.combinedComment &&
                Math.abs(srv.timestamp.getTime() - local.timestamp.getTime()) < 120_000,
            )
          })
          return { ...s, savedData: [...serverSaved, ...stillPending] }
        }),
      )

      setJobQueue((prev) => {
        const otherSession = prev.filter((j) => j.sessionId !== sessionId)
        const local = prev.filter((j) => j.sessionId === sessionId)
        const activeId = confirmingJobIdRef.current

        const mergedPending = pendingJobs.map((pj) => {
          const match = local.find(
            (j) =>
              (j.historyId && j.historyId === pj.historyId) ||
              j.id === pj.id,
          )
          if (match && match.id === activeId) {
            return {
              ...match,
              historyId: pj.historyId || match.historyId,
              originalText: match.originalText || pj.originalText,
            }
          }
          if (match) {
            return {
              ...pj,
              id: match.id,
              suggestions:
                match.suggestions && match.suggestions.length > 0
                  ? match.suggestions
                  : pj.suggestions,
              overallComment: match.overallComment || pj.overallComment,
            }
          }
          return pj
        })

        const pendingHistoryIds = new Set(
          mergedPending.map((j) => j.historyId).filter(Boolean) as string[],
        )
        const pendingClientIds = new Set(mergedPending.map((j) => j.id))

        const inFlight = local.filter(
          (j) => j.status === "queued" || j.status === "processing",
        )
        const localOnly = local.filter(
          (j) =>
            (j.status === "completed" || j.status === "failed") &&
            !j.historyId &&
            j.id !== activeId,
        )
        const activeLocal = activeId
          ? local.find((j) => j.id === activeId)
          : undefined
        const activeAlreadyMerged =
          !!activeId && mergedPending.some((j) => j.id === activeId)

        const extras = [
          ...inFlight,
          ...localOnly,
          ...(activeLocal && !activeAlreadyMerged ? [activeLocal] : []),
        ].filter(
          (j) =>
            (!j.historyId || !pendingHistoryIds.has(j.historyId)) &&
            !pendingClientIds.has(j.id),
        )

        return [...otherSession, ...mergedPending, ...extras]
      })
    } catch (error) {
      console.error("Error loading session details:", error)
    }
  }, [])

  // セッション切り替えハンドラー - 処理中ジョブがある場合は確認
  const handleSessionSwitch = useCallback((sessionId: string) => {
    const hasActiveJobs = jobQueue.some(j => j.status === 'queued' || j.status === 'processing')
    
    if (hasActiveJobs) {
      const confirmed = window.confirm(
        '処理中または待機中のジョブがあります。セッションを切り替えると、これらのジョブは中断されます。続行しますか？'
      )
      if (!confirmed) return
      
      // キューをクリア
      setJobQueue([])
    }
    
    // 生成タイマーの所要時間履歴はセッション寿命内のみのライブ指標のため、
    // 別セッションへ切り替える際はリセットする（design.md Decision 2）。
    // 注意: レビューセグメントの累計（reviewAccumulatedMsRef）はここで
    // 明示的にクリアしない — activeReviewJobIdの判定はQueuedJob.sessionIdと
    // currentSessionIdの一致で行われる（セグメントopen/close effect側で
    // 自動的にクローズ処理される）ため、ここで先にrefを消してしまうと
    // そのeffectのcleanupが正しい経過時間を加算できず、切り替え直前までの
    // レビュー時間を丸ごと失ってしまう。累計を保持しておけば、後で同じ
    // セッション・同じジョブのレビューへ戻った際に加算を再開でき、複数回の
    // 中断・再開をまたいだ累計として正しく扱える（design.md Decision 7）
    if (sessionId !== currentSessionId) {
      setJobTimingHistory([])
    }
    
    setCurrentSessionId(sessionId)
    setSidebarOpen(false)

    // このタブでこのセッションを開くのが初めての場合のみ、ページ再読み込み等で
    // 失われたDraft状態（未確定のAI提案・原文/添削対象テキスト・ジョブキュー）を
    // localStorageから復元する。savedData（サーバー由来）はloadSessionDetailsが
    // 別途フェッチするため、ここでは触れない
    if (!restoredDraftSessionIdsRef.current.has(sessionId)) {
      restoredDraftSessionIdsRef.current.add(sessionId)

      const draft = loadDraftFromStorage(sessionId)
      if (draft) {
        setSessions((prev) =>
          prev.map((s) =>
            s.id === sessionId
              ? {
                  ...s,
                  originalText: draft.originalText || s.originalText,
                  targetText: draft.targetText || s.targetText,
                  exemplarTranslation: draft.exemplarTranslation || s.exemplarTranslation,
                  suggestions: draft.suggestions.length > 0 ? draft.suggestions : s.suggestions,
                  overallComment: draft.overallComment || s.overallComment,
                }
              : s,
          ),
        )
        if (draft.confirmingHistoryIndex !== null) {
          setConfirmingHistoryIndex(draft.confirmingHistoryIndex)
        }
        if (draft.confirmingJobId) {
          setConfirmingJobId(draft.confirmingJobId)
        }
        if (draft.suggestions.length > 0) {
          toast({
            title: "Draftを復元しました",
            description: "前回保存されなかったAI提案（Draft状態）を復元しました",
          })
        }
      }

      const restoredJobs = loadJobQueueFromStorage(sessionId)
      if (restoredJobs.length > 0) {
        setJobQueue(restoredJobs)
        toast({
          title: "ジョブキューを復元しました",
          description: `${restoredJobs.length}件のジョブを復元しました（中断されていた処理は再開待ちに戻しました）`,
        })
      }
    }

    loadSessionDetails(sessionId)
  }, [jobQueue, currentSessionId, loadSessionDetails, toast])

  // Shared-DB refresh: while a session is open, poll histories/proposals so
  // confirmed History and pending Job Queue items appear across browsers/envs.
  useEffect(() => {
    if (!currentSessionId || !session) return
    const POLL_MS = 10_000
    const tick = () => {
      if (typeof document !== "undefined" && document.visibilityState === "hidden") {
        return
      }
      void loadSessionDetails(currentSessionId)
    }
    const id = window.setInterval(tick, POLL_MS)
    return () => window.clearInterval(id)
  }, [currentSessionId, session, loadSessionDetails])

  // 確認中のジョブID（ジョブキューからの確認用）
  const [confirmingJobId, setConfirmingJobId] = useState<string | null>(null)

  useEffect(() => {
    confirmingJobIdRef.current = confirmingJobId
  }, [confirmingJobId])

  // Tracks which confirmingJobId has already triggered the one-time
  // scroll-into-view below, so selecting/deselecting/editing a suggestion
  // (which changes currentSession.suggestions' array reference without
  // changing confirmingJobId) never re-triggers the scroll.
  const lastScrolledJobIdRef = useRef<string | null>(null)

  // Reactive scroll to suggestions card when confirming from job queue.
  // This replaces the setTimeout-based scroll in confirmJob for reliability.
  // Deliberately depends on suggestions.length (not the suggestions array
  // reference itself) so this only re-fires when suggestions first load for
  // a job, not on every in-place suggestion selection/edit mutation
  // (toggleSuggestionSelection/updateSuggestionReason produce a new array
  // reference on every call, which previously caused an unwanted re-scroll
  // to the top of the AI SUGGESTIONS card on every selection change).
  useEffect(() => {
    if (
      confirmingJobId &&
      confirmingJobId !== lastScrolledJobIdRef.current &&
      currentSession?.suggestions &&
      currentSession.suggestions.length > 0
    ) {
      lastScrolledJobIdRef.current = confirmingJobId
      // Small delay to ensure DOM is updated after React render
      const timeoutId = setTimeout(() => {
        const suggestionsCard = document.querySelector('[data-suggestions-card]')
        if (suggestionsCard) {
          suggestionsCard.scrollIntoView({ behavior: 'smooth', block: 'start' })
        }
      }, 50)
      return () => clearTimeout(timeoutId)
    }
    // Intentionally depends on suggestions.length, not the suggestions array
    // reference, to avoid re-scrolling on every selection/edit (see comment above)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [confirmingJobId, currentSession?.suggestions?.length])

  // 「実際にレビュー作業をしている」ジョブID（add-suggestion-generation-timer
  // 改訂、design.md Decision 7）。以下の全てを満たす場合のみ非nullになる:
  //   1. confirmingJobIdがセットされている（HITLレビュー画面を開いている）
  //   2. そのジョブが生成されたセッション（QueuedJob.sessionId）と、現在
  //      表示中のセッション（currentSessionId）が一致している — サイドバーで
  //      別セッションへ切り替えた場合、そのセッションのSuggestionsパネルは
  //      別データを表示する（suggestionsはセッション単位のstateのため）ので
  //      「レビュー中断」として扱う。jobにsessionIdを持たせることで、後で
  //      同じセッションへ戻ってきた際は自動的に再開できる
  //   3. タブが可視状態（isTabVisible） — バックグラウンドタブでは計測しない
  const reviewedJob = confirmingJobId ? jobQueue.find(j => j.id === confirmingJobId) : undefined
  const activeReviewJobId =
    confirmingJobId && reviewedJob && reviewedJob.sessionId === currentSessionId && isTabVisible
      ? confirmingJobId
      : null

  // レビューセグメントのopen/close管理。activeReviewJobIdが変化するたび
  // （レビュー開始・タブ非表示化・別ジョブ/別セッションへの移動・保存など）
  // に前回のセグメントを閉じてreviewAccumulatedMsRefへ加算し、新しい
  // activeReviewJobIdがあれば新規セグメントを開始する。ref更新のみでは
  // 再レンダーが起きないため、セグメントを閉じた瞬間だけnowTickを1回進めて
  // 確定値を表示に反映させる（design.md Decision 7）。
  useEffect(() => {
    if (!activeReviewJobId) return
    const jobId = activeReviewJobId
    // Map自体（reviewSegmentStartRef.current/reviewAccumulatedMsRef.current）は
    // useRef(new Map())で一度だけ生成され、以後差し替えられることはないため
    // ローカル変数へ捕捉してもクリーンアップ実行時点で古い参照になることはない
    // （react-hooks/exhaustive-depsの警告を素直に解消するための捕捉）
    const startMap = reviewSegmentStartRef.current
    const accumulatedMap = reviewAccumulatedMsRef.current
    startMap.set(jobId, Date.now())
    return () => {
      const startedAt = startMap.get(jobId)
      if (startedAt !== undefined) {
        accumulatedMap.set(jobId, (accumulatedMap.get(jobId) || 0) + (Date.now() - startedAt))
        startMap.delete(jobId)
        setNowTick(Date.now())
      }
    }
  }, [activeReviewJobId])

  // レビューセグメントがオープン中のみ、1秒ごとにnowTickを更新してライブの
  // LATEST表示を進める（旧実装はキュー内のqueued/processing状態を対象に
  // していたが、レビュー作業時間のみを計測する方針に変更したため対象を
  // activeReviewJobIdへ変更、design.md Decision 7）。
  useEffect(() => {
    if (!activeReviewJobId) return
    const intervalId = setInterval(() => setNowTick(Date.now()), 1000)
    return () => clearInterval(intervalId)
  }, [activeReviewJobId])

  // ジョブの累計レビュー時間（秒）＝クローズ済みセグメントの合計＋（あれば）
  // 現在オープン中のセグメントのライブ経過時間。保存時の最終値算出とLATEST
  // 表示の両方から使う（design.md Decision 7）。
  const getReviewElapsedSeconds = useCallback(
    (jobId: string) => {
      const accumulatedMs = reviewAccumulatedMsRef.current.get(jobId) || 0
      const openStartedAt = reviewSegmentStartRef.current.get(jobId)
      const liveMs = openStartedAt !== undefined ? nowTick - openStartedAt : 0
      return (accumulatedMs + liveMs) / 1000
    },
    [nowTick],
  )

  // Draft状態（未確定のAI提案・原文/添削対象テキスト等）をlocalStorageへ永続化する。
  // キー入力/選択のたびに書き込まないよう500msデバウンスする
  useEffect(() => {
    if (!currentSessionId || !currentSession) return

    if (draftSaveTimeoutRef.current) {
      clearTimeout(draftSaveTimeoutRef.current)
    }
    draftSaveTimeoutRef.current = setTimeout(() => {
      saveDraftToStorage(currentSessionId, {
        originalText: currentSession.originalText,
        targetText: currentSession.targetText,
        exemplarTranslation: currentSession.exemplarTranslation,
        suggestions: currentSession.suggestions,
        overallComment: currentSession.overallComment,
        confirmingHistoryIndex,
        confirmingJobId,
      })
    }, DRAFT_PERSIST_DEBOUNCE_MS)

    return () => {
      if (draftSaveTimeoutRef.current) {
        clearTimeout(draftSaveTimeoutRef.current)
      }
    }
  }, [currentSessionId, currentSession, confirmingHistoryIndex, confirmingJobId])

  // ジョブキューをセッション単位でlocalStorageへ永続化する（同じデバウンス方針）。
  // processingで中断されたジョブはloadJobQueueFromStorage側でqueuedへ戻される
  useEffect(() => {
    if (!currentSessionId) return

    if (jobQueueSaveTimeoutRef.current) {
      clearTimeout(jobQueueSaveTimeoutRef.current)
    }
    jobQueueSaveTimeoutRef.current = setTimeout(() => {
      saveJobQueueToStorage(currentSessionId, jobQueue)
    }, DRAFT_PERSIST_DEBOUNCE_MS)

    return () => {
      if (jobQueueSaveTimeoutRef.current) {
        clearTimeout(jobQueueSaveTimeoutRef.current)
      }
    }
  }, [currentSessionId, jobQueue])

  // 完了したジョブを確認（HITLフロー）
  const confirmJob = useCallback((job: QueuedJob) => {
    if (!currentSession || job.status !== 'completed') {
      toast({
        title: "エラー",
        description: "確認するジョブが見つかりません",
        variant: "destructive",
      })
      return
    }
    
    // Debug logging for HITL flow
    console.log("[confirmJob] Job data:", {
      id: job.id,
      status: job.status,
      source: job.source,
      suggestionsCount: job.suggestions?.length ?? 0,
      overallComment: job.overallComment?.substring(0, 100),
    })
    
    if (!job.suggestions || job.suggestions.length === 0) {
      // Distinguish between parse failure and "no issues found"
      const isParseFailure = job.overallComment?.includes("抽出できませんでした")
      const errorMessage = isParseFailure
        ? "AI応答のパースに失敗しました。再度お試しください。"
        : job.overallComment
          ? `AIが問題を検出しませんでした: ${job.overallComment}`
          : "このジョブにはAI提案がありません"
      
      console.warn("[confirmJob] No suggestions found:", {
        isParseFailure,
        overallComment: job.overallComment,
      })
      
      toast({
        title: isParseFailure ? "パースエラー" : "提案なし",
        description: errorMessage,
        variant: isParseFailure ? "destructive" : "default",
      })
      return
    }
    
    // ジョブの結果を現在のセッションにロード。
    // job.suggestions はこのジョブのAI生成結果のみを保持しており、ユーザーが
    // カスタム修正カードを追加した後に同じ（または別の）完了済みジョブを
    // 再度クリックしてconfirmJobが再実行されると、その追加分が失われて
    // しまっていた（バグ報告: 「カスタム修正カードが消える」）。ジョブは
    // セッション単位ではなく生成ラウンド単位のデータなので、現在の
    // suggestions内にある isCustom カードは常に保持し、AI提案側だけを
    // job.suggestions で置き換える。
    const preservedCustomSuggestions = currentSession.suggestions.filter((s) => s.isCustom)
    updateCurrentSession({
      ...(job.originalText ? { originalText: job.originalText } : {}),
      targetText: job.targetText,
      suggestions: [...job.suggestions, ...preservedCustomSuggestions],
      overallComment: job.overallComment || '',
    })
    
    setShowCustomForm(true)
    setSelectionCounter(preservedCustomSuggestions.filter((s) => s.selected).length)
    setLastSuggestionSource(job.source ?? null)
    setLastSuggestionModel(job.llmModel ?? null)
    
    // 確認中のジョブIDを記録（ジョブキュー用）
    // Note: useEffect handles scrolling reactively when this is set
    setConfirmingJobId(job.id)
    // 実行履歴の確認インデックスをクリア
    setConfirmingHistoryIndex(null)
    
    toast({
      title: "確認中",
      description: `${job.suggestions.length}件のAI提案をロードしました。内容を確認してください。`,
    })
  }, [currentSession, toast, updateCurrentSession])


  // セッション一覧をAPIから取得
  // 注意: このuseEffectは認証状態(session)の参照が変わるたびに再実行される
  // （Supabaseのトークン自動更新[TOKEN_REFRESHED]や401後の再認証など、ユーザー操作を
  // 伴わないイベントでも発火する）。そのため、既存のsessions状態やlocalStorageの
  // Draftを一切見ずに毎回originalText/targetText等を""へ初期化すると、ユーザーが
  // 入力中/未保存のテキストを無関係なタイミングで消失させてしまう
  // （persist-source-target-text-input変更で修正）。
  // これを避けるため、変換後のセッションへ (1) 直前のsessions状態 (2) localStorageの
  // Draft (3) 空文字のデフォルト、の優先順でテキスト等をマージする。
  const loadSessions = useCallback(async () => {
    try {
      console.log("Loading sessions...")
      const sessionsData: SessionAPIResponse[] = await sessionAPI.getSessions()
      console.log("Sessions data received:", sessionsData)

      setSessions((prev) => {
        const prevById = new Map(prev.map((s) => [s.id, s]))

        // APIから取得したデータをフロントエンドのSession型に変換
        return sessionsData.map((s) => {
          const existing = prevById.get(s.sessionId)
          const draft = existing ? null : loadDraftFromStorage(s.sessionId)

          return {
            id: s.sessionId,
            name: s.name,
            createdAt: new Date(s.createdAt),
            correctionCount: s.correctionCount, // 保存済み件数を追加
            originalText: existing?.originalText || draft?.originalText || "",
            targetText: existing?.targetText || draft?.targetText || "",
            exemplarTranslation:
              existing?.exemplarTranslation || draft?.exemplarTranslation || "",
            suggestions: existing?.suggestions.length
              ? existing.suggestions
              : draft?.suggestions.length
                ? draft.suggestions
                : [],
            overallComment: existing?.overallComment || draft?.overallComment || "",
            // savedData（サーバー由来の実行履歴）はloadSessionDetailsが別途取得するため、
            // 既存の値をそのまま維持する（再取得のたびに空配列へ戻すと再フェッチが必要になる）
            savedData: existing?.savedData || [],
          }
        })
      })
    } catch (error) {
      console.error("Error loading sessions:", error)
    }
  }, [])

  // セッション作成をAPIに保存
  const createNewSession = async () => {
    try {
      const newSessionData = await sessionAPI.createSession(`セッション ${sessions.length + 1}`)
      const newSession: Session = {
        id: newSessionData.sessionId,
        name: newSessionData.name,
        createdAt: new Date(newSessionData.createdAt),
        correctionCount: 0, // 新しいセッションのため0件で初期化
        originalText: "",
        targetText: "",
        exemplarTranslation: "",
        suggestions: [],
        overallComment: "",
        savedData: [],
      }
      setSessions((prev) => [newSession, ...prev])
      setCurrentSessionId(newSession.id)
      setSidebarOpen(false)
      setSelectionCounter(0)
    } catch (error) {
      console.error("Failed to create session:", error)
      toast({
        title: "エラー",
        description: "セッションの作成に失敗しました",
        variant: "destructive",
      })
    }
  }

  // セッション削除をAPIに実行
  const deleteSession = async (sessionId: string) => {
    try {
      await sessionAPI.deleteSession(sessionId)
      setSessions((prev) => prev.filter((s) => s.id !== sessionId))
      if (currentSessionId === sessionId) {
        const remainingSessions = sessions.filter((s) => s.id !== sessionId)
        setCurrentSessionId(remainingSessions.length > 0 ? remainingSessions[0].id : null)
      }
      // セッション削除時は、そのセッションのDraft/ジョブキューも永続化領域から破棄する
      clearDraftFromStorage(sessionId)
      clearJobQueueFromStorage(sessionId)
      restoredDraftSessionIdsRef.current.delete(sessionId)
    } catch (error) {
      console.error("Failed to delete session:", error)
      toast({
        title: "エラー",
        description: "セッションの削除に失敗しました",
        variant: "destructive",
      })
    }
  }

  // 選択時の修正コメントTextareaを内容の高さに自動追従させるための参照とヘルパー。
  // 固定min-heightだと長いコメントが選択前の<p>表示より縮んで見えるバグを防ぐ。
  const suggestionTextareaRefs = useRef<Record<string, HTMLTextAreaElement | null>>({})

  const resizeSuggestionTextarea = (el: HTMLTextAreaElement | null) => {
    if (!el) return
    el.style.height = "auto"
    el.style.height = `${el.scrollHeight}px`
  }

  // 提案が選択された/編集された/再生成された/履歴から復元された場合に、
  // 現在マウント中の全Textareaの高さを再計算する
  useEffect(() => {
    Object.values(suggestionTextareaRefs.current).forEach(resizeSuggestionTextarea)
  }, [currentSession?.suggestions])

  const toggleSuggestionSelection = (suggestionId: string) => {
    if (!currentSession) return

    const suggestion = currentSession.suggestions.find((s) => s.id === suggestionId)
    if (!suggestion) return

    let newCounter = selectionCounter
    let newSelectedOrder: number | undefined

    if (!suggestion.selected) {
      // 選択する場合
      newCounter += 1
      newSelectedOrder = newCounter
    } else {
      // 選択解除する場合
      const currentOrder = suggestion.selectedOrder
      if (currentOrder) {
        // より大きな順序番号を持つ項目の番号を1つずつ減らす
        const updatedSuggestions = currentSession.suggestions.map((s) => {
          if (s.selectedOrder && s.selectedOrder > currentOrder) {
            return { ...s, selectedOrder: s.selectedOrder - 1 }
          }
          return s
        })
        updateCurrentSession({ suggestions: updatedSuggestions })
        newCounter -= 1
      }
      newSelectedOrder = undefined
    }

    const updatedSuggestions = currentSession.suggestions.map((s) =>
      s.id === suggestionId ? { ...s, selected: !s.selected, selectedOrder: newSelectedOrder } : s,
    )

    updateCurrentSession({ suggestions: updatedSuggestions })
    setSelectionCounter(newCounter)
  }

  const updateSuggestionReason = (suggestionId: string, newReason: string) => {
    if (!currentSession) return

    const updatedSuggestions = currentSession.suggestions.map((suggestion) =>
      suggestion.id === suggestionId ? { ...suggestion, userModifiedReason: newReason } : suggestion,
    )
    updateCurrentSession({ suggestions: updatedSuggestions })
  }

  const addCustomCorrection = () => {
    if (!currentSession || !customCorrection.original || !customCorrection.reason) {
      toast({
        title: "入力エラー",
        description: "すべての項目を入力してください",
        variant: "destructive",
      })
      return
    }

    const newCounter = selectionCounter + 1
    const newSuggestion: CorrectionSuggestion = {
      id: `custom-${Date.now()}`,
      original: customCorrection.original,
      reason: customCorrection.reason,
      selected: true,
      selectedOrder: newCounter,
      isCustom: true,
    }

    updateCurrentSession({
      suggestions: [...currentSession.suggestions, newSuggestion],
    })

    setCustomCorrection({ original: "", reason: "" })
    setSelectionCounter(newCounter)

    toast({
      title: "修正内容を追加しました",
      description: "カスタム修正内容が追加され、自動的に選択されました",
    })
  }

  // TARGET TEXTでのマウス選択（ネイティブのテキスト選択、指摘スパンの
  // ハイライトオーバーレイとは別物）を、カスタム修正カードの「指摘箇所」
  // フィールドへ自動反映する。選択が空/未ドラッグ（カーソル移動のみ）の
  // 場合は発火しない。修正コメント欄は上書きしない。フォームが閉じている
  // 場合は自動的に開く — 開かないと入力内容が反映されたことに気付けない
  // ため（openspec/changes/highlight-suggestion-text-spans/tasks.md 参照）。
  const handleTargetTextSelect = (e: React.SyntheticEvent<HTMLTextAreaElement>) => {
    const { selectionStart, selectionEnd, value } = e.currentTarget
    if (selectionStart === selectionEnd) return
    const selectedText = value.substring(selectionStart, selectionEnd)
    if (!selectedText) return
    setCustomCorrection((prev) => ({ ...prev, original: selectedText }))
    setShowCustomForm(true)
  }

  const copyToClipboard = async (text: string, description: string = "クリップボードにコピーしました") => {
    try {
      await navigator.clipboard.writeText(text)
      toast({
        title: "コピー完了",
        description,
      })
    } catch {
      toast({
        title: "コピー失敗",
        description: "クリップボードへのコピーに失敗しました",
        variant: "destructive",
      })
    }
  }

  // 確定してコピー・保存: クリップボード＋ローカル UI 確定を先に行い、
  // 履歴/提案の API 永続化はバックグラウンドで続行する
  // （async-confirm-copy-background-save）。
  const saveCorrections = async () => {
    if (!currentSession) return

    // 二重クリック/連続送信ガード: コピー〜バックグラウンド保存が完了するまで
    // 再入を防ぎ、同一の生成ラウンドから複数の「添削データ」エントリが誤って
    // 作成されることを防止する
    if (isSaving) return

    const selectedSuggestions = currentSession.suggestions
      .filter((s) => s.selected)
      .sort((a, b) => (a.selectedOrder || 0) - (b.selectedOrder || 0))

    if (selectedSuggestions.length < 3) {
      toast({
        title: "選択不足",
        description: "3つ以上の修正内容を選択してください",
        variant: "destructive",
      })
      return
    }

    // 原文/添削対象テキストが保存時点で空だと、バックエンドの/historiesが
    // 400を返し、以降の/proposals呼び出しがhistoryId欠落でエラーになる
    // （ブラウザ上は「Failed to fetch」としか見えない）。ここで先に検知する。
    if (!currentSession.originalText.trim() || !currentSession.targetText.trim()) {
      toast({
        title: "テキストが空です",
        description: "原文と添削対象テキストの両方が必要です",
        variant: "destructive",
      })
      return
    }

    // API / ローカル確定用にクリア前のスナップショットを保持する
    const sessionId = currentSession.id
    const originalText = currentSession.originalText
    const targetText = currentSession.targetText
    const overallComment = currentSession.overallComment
    const suggestionsSnapshot = currentSession.suggestions
    const jobIdToConfirm = confirmingJobId
    const historyIndexToConfirm = confirmingHistoryIndex
    const pendingHistoryId =
      jobIdToConfirm !== null
        ? jobQueue.find((j) => j.id === jobIdToConfirm)?.historyId
        : undefined

    const numberedCorrections = selectedSuggestions
      .map((suggestion, index) => {
        const reasonText = suggestion.userModifiedReason || suggestion.reason
        return `${index + 1}.${suggestion.original}\n${reasonText}`
      })
      .join("\n\n")
    const combinedComment = `${numberedCorrections}\n\n${overallComment}`
    const commitTimestamp = new Date()
    const shouldAppendSavedData = historyIndexToConfirm === null

    setIsSaving(true)
    try {
      // 1) クリップボード（ネットワークを待たない）
      try {
        await navigator.clipboard.writeText(combinedComment)
      } catch {
        toast({
          title: "コピー失敗",
          description: "クリップボードへのコピーに失敗しました",
          variant: "destructive",
        })
        return
      }

      // 2) ローカル UI 確定（historyId は後でパッチ）
      if (jobIdToConfirm !== null) {
        const savedData: SavedData = {
          originalText,
          instructionPrompt: "CCTalkからの添削指示",
          targetText,
          aiSuggestions: suggestionsSnapshot,
          selectedCorrections: selectedSuggestions,
          overallComment,
          combinedComment,
          timestamp: commitTimestamp,
          confirmed: true,
        }

        setSessions((prev) =>
          prev.map((session) =>
            session.id === sessionId
              ? {
                  ...session,
                  savedData: [...session.savedData, savedData],
                  targetText: "",
                  suggestions: [],
                  overallComment: "",
                }
              : session,
          ),
        )

        // このジョブの累計レビュー作業時間（キュー待機/AI処理時間を含まない）を
        // 記録する（add-suggestion-generation-timer改訂、design.md Decision 7）。
        // getReviewElapsedSecondsはクローズ済みセグメント＋現在オープン中の
        // セグメントを合算するので、setConfirmingJobId(null)より前に呼び出す
        const timedJob = jobQueue.find((j) => j.id === jobIdToConfirm)
        if (timedJob) {
          const elapsedSeconds = getReviewElapsedSeconds(timedJob.id)
          setJobTimingHistory((prev) =>
            [
              ...prev,
              { jobId: timedJob.id, elapsedSeconds, completedAt: new Date() },
            ].slice(-MAX_JOB_TIMING_HISTORY),
          )
          reviewAccumulatedMsRef.current.delete(timedJob.id)
          reviewSegmentStartRef.current.delete(timedJob.id)
        }

        setJobQueue((prev) => prev.filter((j) => j.id !== jobIdToConfirm))
        setConfirmingJobId(null)
        clearDraftFromStorage(sessionId)
      } else if (historyIndexToConfirm !== null) {
        setSessions((prev) =>
          prev.map((session) =>
            session.id === sessionId
              ? {
                  ...session,
                  savedData: session.savedData.map((data, idx) =>
                    idx === historyIndexToConfirm ? { ...data, confirmed: true } : data,
                  ),
                  targetText: "",
                  suggestions: [],
                  overallComment: "",
                }
              : session,
          ),
        )
        setConfirmingHistoryIndex(null)
        clearDraftFromStorage(sessionId)
      } else {
        const savedData: SavedData = {
          originalText,
          instructionPrompt: "CCTalkからの添削指示",
          targetText,
          aiSuggestions: suggestionsSnapshot,
          selectedCorrections: selectedSuggestions,
          overallComment,
          combinedComment,
          timestamp: commitTimestamp,
          confirmed: true,
        }

        setSessions((prev) =>
          prev.map((session) =>
            session.id === sessionId
              ? {
                  ...session,
                  savedData: [...session.savedData, savedData],
                  targetText: "",
                  suggestions: [],
                  overallComment: "",
                }
              : session,
          ),
        )
        clearDraftFromStorage(sessionId)
      }

      setShowCustomForm(false)
      setCustomCorrection({ original: "", reason: "" })
      setSelectionCounter(0)

      toast({
        title: "コピー完了",
        description: "修正内容をクリップボードにコピーしました。サーバーへ保存しています...",
      })

      // 3) バックグラウンドで履歴/提案を永続化
      // pending 生成済みなら PUT で promote（二重 History を避ける）
      try {
        const selectedIdsJson = JSON.stringify(selectedSuggestions.map((s) => s.id))
        const customJson = JSON.stringify(selectedSuggestions.filter((s) => s.isCustom))
        let resolvedHistoryId = pendingHistoryId

        if (pendingHistoryId) {
          await historyAPI.updateHistory(pendingHistoryId, {
            status: "confirmed",
            combinedComment: overallComment,
            overallComment,
            selectedProposalIds: selectedIdsJson,
            customProposals: customJson,
          })
          for (const suggestion of suggestionsSnapshot) {
            const looksLikeUuid =
              typeof suggestion.id === "string" &&
              /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(
                suggestion.id,
              )
            if (looksLikeUuid && !suggestion.isCustom) {
              await proposalAPI.updateProposal(suggestion.id, {
                isSelected: !!suggestion.selected,
                isModified: !!suggestion.userModifiedReason,
                modifiedAfterText: suggestion.original,
                modifiedReason: suggestion.userModifiedReason || suggestion.reason,
                selectedOrder: suggestion.selected ? suggestion.selectedOrder : null,
              })
            } else if (suggestion.isCustom || !looksLikeUuid) {
              // レビュー中に追加したカスタム、または persist 前のローカル id
              await proposalAPI.createProposal({
                historyId: pendingHistoryId,
                type: suggestion.isCustom ? "Custom" : "AI",
                originalAfterText: suggestion.original,
                originalReason: suggestion.reason,
                modifiedAfterText: suggestion.original,
                modifiedReason: suggestion.userModifiedReason || suggestion.reason,
                isSelected: !!suggestion.selected,
                isModified: !!suggestion.userModifiedReason,
                isCustom: !!suggestion.isCustom,
                selectedOrder: suggestion.selected ? suggestion.selectedOrder : undefined,
              })
            }
          }
        } else {
          const historyData = {
            sessionId,
            originalText,
            targetText,
            instructionPrompt: "CCTalkからの添削指示",
            combinedComment: overallComment,
            overallComment,
            status: "confirmed" as const,
            selectedProposalIds: selectedIdsJson,
            customProposals: customJson,
            // No pending row to promote (restored round, or the generation-time
            // save failed), so carry the provenance of the round on screen.
            ...(lastSuggestionModel
              ? {
                  llmProvider: lastSuggestionSource === "webllm" ? "webllm" : "api",
                  llmModel: lastSuggestionModel,
                }
              : {}),
          }

          const savedHistory = await historyAPI.createHistory(historyData)
          if (!savedHistory?.historyId) {
            throw new Error("履歴の保存に失敗しました（historyIdが返却されませんでした）")
          }
          resolvedHistoryId = savedHistory.historyId

          for (const suggestion of suggestionsSnapshot) {
            await proposalAPI.createProposal({
              historyId: savedHistory.historyId,
              type: (suggestion.isCustom ? "Custom" : "AI") as "AI" | "Custom",
              originalAfterText: suggestion.original,
              originalReason: suggestion.reason,
              modifiedAfterText: suggestion.original,
              modifiedReason: suggestion.userModifiedReason || suggestion.reason,
              isSelected: !!suggestion.selected,
              isModified: !!suggestion.userModifiedReason,
              isCustom: !!suggestion.isCustom,
              selectedOrder: suggestion.selected ? suggestion.selectedOrder : undefined,
            })
          }
        }

        if (shouldAppendSavedData && resolvedHistoryId) {
          setSessions((prev) =>
            prev.map((session) => {
              if (session.id !== sessionId) return session
              return {
                ...session,
                savedData: session.savedData.map((d) =>
                  d.combinedComment === combinedComment &&
                  d.timestamp instanceof Date &&
                  d.timestamp.getTime() === commitTimestamp.getTime()
                    ? { ...d, historyId: resolvedHistoryId }
                    : d,
                ),
              }
            }),
          )
        }

        toast({
          title: "保存完了",
          description:
            jobIdToConfirm !== null
              ? "ジョブを確認済みにし、サーバーに保存しました。"
              : historyIndexToConfirm !== null
                ? "履歴を確認済みにし、サーバーに保存しました。"
                : "修正内容をサーバーに保存しました。",
        })
      } catch (saveError) {
        console.error("Failed to save corrections:", saveError)
        toast({
          title: "保存失敗",
          description: "コピーは完了しましたが、サーバーへの保存に失敗しました",
          variant: "destructive",
        })
      }
    } finally {
      setIsSaving(false)
    }
  }

  // 履歴をAPIから復元
  const restoreFromHistory = (savedData: SavedData) => {
    if (!currentSession) return

    updateCurrentSession({
      originalText: savedData.originalText,
      targetText: savedData.targetText,
      suggestions: savedData.aiSuggestions.map((s) => ({
        ...s,
        selected: s.selected || false,
        selectedOrder: s.selectedOrder,
      })),
      overallComment: savedData.overallComment,
    })

    // 選択カウンターを復元
    const selectedCount = savedData.aiSuggestions.filter((s) => s.selected).length
    setSelectionCounter(selectedCount)

    // Rounds saved before provenance existed have no model to show.
    setLastSuggestionSource(
      savedData.llmProvider === "webllm" ? "webllm" : savedData.llmProvider ? "api" : null,
    )
    setLastSuggestionModel(savedData.llmModel ?? null)

    setShowCustomForm(true)

    toast({
      title: "確認中",
      description: "履歴データをロードしました。内容を確認して「確定してコピー・保存」を実行してください。",
    })
  }

  // 添削データ（履歴ラウンド）のアーカイブ（ソフトデリート、完全削除ではない）
  const archiveHistoryRound = async (data: SavedData, index: number) => {
    if (!currentSession) return

    try {
      if (data.historyId) {
        await historyAPI.archiveHistory(data.historyId)
      }

      // 楽観的UI更新: ローカル状態からラウンドを除去
      updateCurrentSession({
        savedData: currentSession.savedData.filter((_, idx) => idx !== index),
      })

      if (confirmingHistoryIndex === index) {
        setConfirmingHistoryIndex(null)
      }

      toast({
        title: "アーカイブ完了",
        description: "添削データをアーカイブしました",
      })
    } catch (error) {
      console.error("Failed to archive history:", error)
      toast({
        title: "エラー",
        description: "添削データのアーカイブに失敗しました",
        variant: "destructive",
      })
    }
  }

  const selectedCount = currentSession?.suggestions.filter((s) => s.selected).length || 0
  const canSave = selectedCount >= 3

  // Text-span highlight ranges for the SOURCE/TARGET TEXT textareas, driven
  // by the hover-preview and selected-persistent triggers (see
  // highlight-suggestion-text-spans design.md Decision 2). Graceful
  // no-match handling (empty/absent field, or substring not found) is
  // handled inside HighlightedTextarea itself.
  const targetHighlights: TextHighlight[] = useMemo(() => {
    if (!currentSession) return []
    return currentSession.suggestions
      .filter((s) => s.selected || s.id === hoveredSuggestionId)
      .map((s) => ({
        text: s.original,
        variant: (s.id === hoveredSuggestionId ? "hover" : "selected") as TextHighlight["variant"],
      }))
  }, [currentSession, hoveredSuggestionId])

  const sourceHighlights: TextHighlight[] = useMemo(() => {
    if (!currentSession) return []
    return currentSession.suggestions
      .filter((s) => (s.selected || s.id === hoveredSuggestionId) && s.sourceExcerpt)
      .map((s) => ({
        text: s.sourceExcerpt as string,
        variant: (s.id === hoveredSuggestionId ? "hover" : "selected") as TextHighlight["variant"],
      }))
  }, [currentSession, hoveredSuggestionId])

  // Filter sessions based on search query
  const filteredSessions = sessions.filter((s) =>
    s.name.toLowerCase().includes(sessionSearch.toLowerCase())
  )

  // ドッキング表示のカラムとフローティングのオーバーレイは同じ一覧を出す。
  // 以前は同一のJSXが2箇所に複製されており、片方だけ変更されるドリフトの
  // 原因になっていたため、1つの描画ヘルパーに統合している
  // （floating-session-pane-and-collapsible-panels design.md Decision 2）。
  // handleSessionSwitch 自身が sidebarOpen を閉じるので、選択時にオーバーレイは
  // 自動的に閉じる。
  const sessionListItems = (
    <div className="space-y-2">
      {filteredSessions.map((s) => (
        <div
          key={s.id}
          className={`group p-3 rounded-lg border cursor-pointer transition-colors ${
            currentSessionId === s.id
              ? "bg-primary-container border-md3-primary"
              : "border-outline-variant hover:bg-surface-container"
          }`}
          onClick={() => handleSessionSwitch(s.id)}
        >
          <div className="flex items-start justify-between">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined md-18 text-on-surface-variant">description</span>
                <h3 className="font-semibold text-body-sm text-on-surface truncate">{s.name}</h3>
              </div>
              <div className="flex items-center gap-2 mt-1 ml-6">
                <span className="material-symbols-outlined md-18 text-on-surface-variant">calendar_today</span>
                <span className="text-metadata text-on-surface-variant">{s.createdAt.toLocaleDateString()}</span>
              </div>
              <div className="mt-2 ml-6">
                <Badge
                  className={`text-xs font-medium ${
                    s.correctionCount > 0
                      ? 'bg-session-complete text-white'
                      : 'bg-session-empty text-white'
                  }`}
                >
                  {s.correctionCount > 0 ? `${s.correctionCount} Saved` : 'Draft'}
                </Badge>
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={(e) => {
                e.stopPropagation()
                deleteSession(s.id)
              }}
              className="opacity-0 group-hover:opacity-100 transition-opacity p-1 h-auto"
            >
              <span className="material-symbols-outlined md-18 text-on-surface-variant">delete</span>
            </Button>
          </div>
        </div>
      ))}
      {filteredSessions.length === 0 && (
        <div className="text-center py-8 text-on-surface-variant">
          <span className="material-symbols-outlined md-36 mx-auto mb-2 opacity-50">description</span>
          <p className="text-body-sm">セッションがありません</p>
        </div>
      )}
    </div>
  )

  const sessionSearchInput = (
    <Input
      placeholder="セッションを検索..."
      value={sessionSearch}
      onChange={(e) => setSessionSearch(e.target.value)}
      className="bg-surface-container border-outline-variant"
    />
  )

  // Job Queue panel: in-flight work
  const activeJobCount = jobQueue.filter(j => j.status === 'processing' || j.status === 'queued').length
  // Job Queue横スライドの並び順。実行中 → 待機中 → 完了 → 失敗、各グループ内は
  // 新しい順（slide-job-queue-carousel change、design.md Decision 2参照）。
  const orderedJobQueue = useMemo(() => sortJobsByRelevance(jobQueue), [jobQueue])
  // TopAppBar bell: completed jobs awaiting HITL confirm/save.
  // Job Queueと同じヘルパーを使い「最新」の定義が2箇所でズレないようにする。
  const completedJobs = useMemo(() => sortCompletedJobsNewestFirst(jobQueue), [jobQueue])
  const completedJobCount = completedJobs.length

  // 生成タイマー表示用の派生値（add-suggestion-generation-timer改訂、design.md
  // Decision 7参照）。「最新」はキュー待機/AI処理時間を含まない、レビュー
  // 作業時間のみを表す点が当初実装からの変更点:
  // - confirmingJobIdがセットされている間（＝そのジョブのHITLレビュー画面を
  //   開いている間）は、そのジョブの累計レビュー時間（getReviewElapsedSeconds）
  //   をライブ表示する。activeReviewJobIdと一致する間だけ実際にticking
  //   （タブ可視・かつ現在のセッションと一致）し、タブが非表示または別
  //   セッションへ切り替え中は値はそのまま（一時停止）で表示され続ける。
  // - confirmingJobIdがnull（レビュー画面を閉じている/まだ何も確認していない）
  //   の場合は、直近に確定保存されたジョブの確定済みレビュー時間を表示する。
  // 「平均」はこのブラウザセッション中に確定保存された全ジョブ（＝レビュー
  // 作業時間）の単純平均（セッション切り替えでリセットされる、design.md
  // Decision 2、この平均の算出方法自体は変更なし）。
  const formatJobDuration = (seconds: number) => `${seconds.toFixed(1)}秒`

  const latestCompletedTiming = jobTimingHistory.length > 0 ? jobTimingHistory[jobTimingHistory.length - 1] : null
  const latestJobDurationSeconds = confirmingJobId
    ? getReviewElapsedSeconds(confirmingJobId)
    : latestCompletedTiming?.elapsedSeconds ?? null
  const isLatestJobLive = activeReviewJobId !== null && activeReviewJobId === confirmingJobId
  // レビュー中だが計測が一時停止中（タブ非表示 or 別セッションへ切り替え中）
  // であることを示す。この状態のジョブはまだ確定保存されていないため、
  // 「保存済み」を意味するbg-session-completeでは表示しない（design.md
  // Decision 7）。
  const isReviewPaused = confirmingJobId !== null && !isLatestJobLive
  const averageJobDurationSeconds =
    jobTimingHistory.length > 0
      ? jobTimingHistory.reduce((sum, r) => sum + r.elapsedSeconds, 0) / jobTimingHistory.length
      : null

  // Coming Soon Placeholder component
  const ComingSoonPlaceholder = ({ title }: { title: string }) => (
    <div className="flex-1 flex items-center justify-center bg-surface-container-low">
      <Card className="max-w-md w-full mx-4 bg-surface border-outline-variant">
        <CardHeader className="text-center">
          <span className="material-symbols-outlined md-48 mx-auto mb-4 text-on-surface-variant">
            construction
          </span>
          <CardTitle className="text-headline-md text-on-surface">{title}</CardTitle>
          <CardDescription className="text-body-sm text-on-surface-variant">
            この機能は現在開発中です。今後のアップデートをお待ちください。
          </CardDescription>
        </CardHeader>
        <CardContent className="text-center">
          <Badge variant="secondary" className="bg-surface-container text-on-surface-variant">
            Coming Soon
          </Badge>
        </CardContent>
      </Card>
    </div>
  )

  // セッション一覧を初期化時に読み込み（認証済みの場合のみ）
  useEffect(() => {
    if (session) {
      loadSessions()
    }
  }, [session, loadSessions])

  // 認証状態を確認中はローディング表示
  if (isAuthLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface-container-low">
        <span className="material-symbols-outlined md-48 animate-spin text-md3-primary">progress_activity</span>
      </div>
    )
  }

  // 未認証の場合はログイン画面を表示し、保護されたエンドポイントへのアクセスを行わない
  if (!session) {
    return <LoginScreen />
  }

  return (
    <div className="h-screen flex flex-col bg-surface-container-low">
      {/* TopAppBar */}
      <header className="h-16 bg-surface border-b border-outline-variant flex items-center px-4 gap-4 flex-shrink-0 z-50">
        {/* Session pane trigger — 全ブレークポイントで常に見えるので一覧が
            迷子にならない。ドッキング中に押すとカラムをたたんで作業領域を
            広げ、フローティング中はオーバーレイを開閉する。 */}
        <button
          type="button"
          onClick={toggleSessionPane}
          className="p-2 rounded-full hover:bg-surface-container transition-colors focus-visible:ring-2 focus-visible:ring-md3-primary"
          title={
            isSessionPaneDocked
              ? 'セッション一覧をたたむ'
              : sidebarOpen
                ? 'セッション一覧を閉じる'
                : 'セッション一覧を開く'
          }
          aria-label={
            isSessionPaneDocked
              ? 'セッション一覧をたたむ'
              : sidebarOpen
                ? 'セッション一覧を閉じる'
                : 'セッション一覧を開く'
          }
          aria-expanded={isSessionPaneDocked || sidebarOpen}
        >
          <span className="material-symbols-outlined md-24 text-on-surface-variant">
            {sidebarOpen ? 'menu_open' : 'menu'}
          </span>
        </button>

        {/* Logo/Title - Text wordmark only, no icon */}
        <h1 className="text-headline-lg text-on-surface">MJAI</h1>

        {/* Navigation Tabs */}
        <nav className="flex items-center gap-1 ml-4">
          <button
            onClick={() => setActiveNav('sessions')}
            className={`px-4 py-2 text-body-sm rounded-lg transition-colors ${
              activeNav === 'sessions'
                ? 'bg-primary-container text-on-primary-container font-semibold'
                : 'text-on-surface-variant hover:bg-surface-container font-normal'
            }`}
          >
            Sessions
          </button>
          <button
            onClick={() => setActiveNav('dashboard')}
            className={`px-4 py-2 text-body-sm rounded-lg transition-colors ${
              activeNav === 'dashboard'
                ? 'bg-primary-container text-on-primary-container font-semibold'
                : 'text-on-surface-variant hover:bg-surface-container font-normal'
            }`}
          >
            Dashboard
          </button>
          <button
            onClick={() => setActiveNav('archive')}
            className={`px-4 py-2 text-body-sm rounded-lg transition-colors ${
              activeNav === 'archive'
                ? 'bg-primary-container text-on-primary-container font-semibold'
                : 'text-on-surface-variant hover:bg-surface-container font-normal'
            }`}
          >
            Archive
          </button>
        </nav>

        {/* New Session Button */}
        <Button
          onClick={createNewSession}
          size="sm"
          className="ml-auto hidden sm:flex bg-md3-primary text-on-primary hover:bg-md3-primary/90 font-semibold"
        >
          <span className="material-symbols-outlined md-18 mr-1">add</span>
          New Session
        </Button>
        <Button
          onClick={createNewSession}
          size="icon"
          className="ml-auto sm:hidden bg-md3-primary text-on-primary hover:bg-md3-primary/90"
        >
          <span className="material-symbols-outlined md-20">add</span>
        </Button>

        {/* Right side icons */}
        <div className="flex items-center gap-2">
          {/* Notification Bell — badge = completed awaiting HITL */}
          <div className="relative" ref={bellPanelRef}>
            <button
              type="button"
              className={`p-2 rounded-full hover:bg-surface-container transition-colors relative ${bellShake ? 'bell-shake' : ''}`}
              title="完了通知"
              aria-label="完了通知"
              aria-expanded={bellPanelOpen}
              aria-haspopup="true"
              onClick={() => setBellPanelOpen((open) => !open)}
            >
              <span className="material-symbols-outlined md-24 text-on-surface-variant">notifications</span>
              {completedJobCount > 0 && (
                <span className="absolute -top-1 -right-1 bg-error text-on-error text-xs font-medium rounded-full w-5 h-5 flex items-center justify-center">
                  {completedJobCount}
                </span>
              )}
            </button>
            {bellPanelOpen && (
              <div
                className="absolute right-0 top-full mt-2 w-80 max-w-[calc(100vw-2rem)] bg-surface border border-outline-variant z-50"
                role="menu"
                aria-label="完了ジョブ一覧"
              >
                <div className="px-3 py-2 border-b border-outline-variant">
                  <p className="text-label-caps tracking-wider text-on-surface-variant uppercase">
                    Notifications
                  </p>
                  <p className="text-metadata text-on-surface-variant mt-0.5">
                    確認待ちの完了ジョブ
                  </p>
                </div>
                {completedJobs.length === 0 ? (
                  <p className="px-3 py-6 text-body-sm text-on-surface-variant text-center">
                    確認待ちの完了ジョブはありません
                  </p>
                ) : (
                  <ul className="py-1 max-h-80 overflow-y-auto">
                    {completedJobs.map((job) => {
                      const time = job.completedAt ?? job.queuedAt
                      const snippet = deriveCorrectionLabel(job).text
                      return (
                        <li key={job.id}>
                          <button
                            type="button"
                            role="menuitem"
                            className="w-full text-left px-3 py-2.5 hover:bg-surface-container transition-colors border-b border-outline-variant last:border-b-0"
                            onClick={() => {
                              confirmJob(job)
                              setBellPanelOpen(false)
                            }}
                          >
                            <div className="flex items-center gap-2">
                              <span className="material-symbols-outlined md-18 text-session-complete">
                                check_circle
                              </span>
                              <Badge variant="outline" className="text-xs font-medium">
                                完了
                              </Badge>
                              <span className="text-metadata text-on-surface-variant ml-auto">
                                {time.toLocaleTimeString()}
                              </span>
                            </div>
                            <p className="text-body-sm text-on-surface mt-1 truncate">
                              {snippet}
                            </p>
                          </button>
                        </li>
                      )
                    })}
                  </ul>
                )}
              </div>
            )}
          </div>

          {/* Settings (shared AI correction prompt) */}
          <button
            onClick={() => setPromptSettingsOpen(true)}
            className="p-2 rounded-full hover:bg-surface-container transition-colors"
            title="設定"
            aria-label="設定"
          >
            <span className="material-symbols-outlined md-24 text-on-surface-variant">settings</span>
          </button>

          {/* User Avatar */}
          {avatarUrl ? (
            <Image
              src={avatarUrl}
              alt="User avatar"
              width={32}
              height={32}
              className="rounded-full border border-outline-variant"
              unoptimized
            />
          ) : (
            <span className="material-symbols-outlined md-24 text-on-surface-variant">account_circle</span>
          )}

          {/* Logout Button */}
          <button
            onClick={() => signOut()}
            className="p-2 rounded-full hover:bg-surface-container transition-colors"
            title="ログアウト"
          >
            <span className="material-symbols-outlined md-24 text-on-surface-variant">logout</span>
          </button>
        </div>
      </header>

      {/* Floating Session Panel — 全ブレークポイント共通。Radix Dialog由来の
          Sheetがバックドロップ・Esc・フォーカストラップ・トリガーへの
          フォーカス復帰を提供する（design.md Decision 2）。 */}
      <Sheet open={sidebarOpen} onOpenChange={setSidebarOpen}>
        <SheetContent side="left" className="w-80 p-0 bg-surface">
          <SheetHeader className="p-4 pr-12 border-b border-outline-variant">
            <div className="flex items-center justify-between gap-2">
              <SheetTitle className="text-headline-md text-on-surface">セッション</SheetTitle>
              {isLgScreen && (
                <button
                  type="button"
                  onClick={dockSessionPane}
                  className="p-2 rounded-full hover:bg-surface-container transition-colors focus-visible:ring-2 focus-visible:ring-md3-primary"
                  title="セッション一覧を左に固定する"
                  aria-label="セッション一覧を左に固定する"
                >
                  <span className="material-symbols-outlined md-20 text-on-surface-variant">
                    dock_to_left
                  </span>
                </button>
              )}
            </div>
          </SheetHeader>
          <div className="p-4">
            <div className="mb-4">{sessionSearchInput}</div>
            <ScrollArea className="h-[calc(100vh-12rem)]">{sessionListItems}</ScrollArea>
          </div>
        </SheetContent>
      </Sheet>

      {/* Main Content Area */}
      {activeNav === 'dashboard' && <ComingSoonPlaceholder title="Dashboard" />}
      {activeNav === 'archive' && <ComingSoonPlaceholder title="Archive" />}
      {activeNav === 'sessions' && (
        <div className="flex flex-1 min-h-0">
          {/* Left Pane - Session List。ドッキング時のみレイアウト内に w-72 の
              カラムとして存在する。フローティング時はDOMから外れ、その幅は
              そのままセンター/右ペーンの作業領域になる。 */}
          {isSessionPaneDocked && (
            <aside
              className="hidden lg:flex lg:flex-col w-72 bg-surface border-r border-outline-variant flex-shrink-0"
              aria-label="セッション一覧"
            >
              <div className="p-4 border-b border-outline-variant">{sessionSearchInput}</div>
              <ScrollArea className="flex-1 p-4">{sessionListItems}</ScrollArea>
            </aside>
          )}

          {/* Center + Right Pane Container */}
          <div className="flex-1 flex flex-col lg:flex-row min-h-0 overflow-hidden">
            {/* Center Pane - Editor */}
            <main className="flex-1 overflow-y-auto p-4 lg:p-6">
              {!currentSession ? (
                <div className="flex items-center justify-center min-h-[calc(100vh-8rem)]">
                  <Card className="max-w-md w-full mx-4 bg-surface border-outline-variant">
                    <CardHeader className="text-center">
                      <span className="material-symbols-outlined md-48 mx-auto mb-4 text-md3-primary">description</span>
                      <CardTitle className="text-headline-md text-on-surface">セッションを開始</CardTitle>
                      <CardDescription className="text-body-sm text-on-surface-variant">
                        新しいセッションを作成して添削を開始しましょう
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <Button onClick={createNewSession} className="w-full bg-md3-primary text-on-primary hover:bg-md3-primary/90" size="lg">
                        新しいセッション作成
                      </Button>
                    </CardContent>
                  </Card>
                </div>
              ) : (
                <div className="space-y-6">
                  {/* Session Header */}
                  <div className="flex items-center justify-between">
                    <div>
                      <h2 className="text-headline-lg text-on-surface">{currentSession.name}</h2>
                      <p className="text-metadata text-on-surface-variant">作成日: {currentSession.createdAt.toLocaleString()}</p>
                    </div>
                    <div className="flex items-center gap-3">
                      {/* レビュー作業時間タイマー＋平均（add-suggestion-generation-timer
                          改訂、design.md Decision 7）。LATESTはレビュー中のジョブの
                          累計レビュー時間（キュー待機/AI処理時間を含まない）。
                          タブ非表示/別セッション切り替え中は一時停止し、一時停止アイコン
                          で示す（保存済みを意味するbg-session-completeとは区別する）。 */}
                      <div className="flex items-center gap-1.5">
                        <span className="text-label-caps text-on-surface-variant">LATEST</span>
                        <Badge
                          className={`text-xs font-medium ${
                            isLatestJobLive || isReviewPaused
                              ? 'bg-surface-container text-on-surface-variant'
                              : latestJobDurationSeconds !== null
                                ? 'bg-session-complete text-white'
                                : 'bg-surface-container text-on-surface-variant'
                          }`}
                        >
                          {isLatestJobLive && (
                            <span className="material-symbols-outlined md-18 animate-spin mr-1 align-middle">progress_activity</span>
                          )}
                          {isReviewPaused && (
                            <span className="material-symbols-outlined md-18 mr-1 align-middle">pause_circle</span>
                          )}
                          {latestJobDurationSeconds !== null ? formatJobDuration(latestJobDurationSeconds) : '—'}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span className="text-label-caps text-on-surface-variant">AVG</span>
                        <Badge className="bg-surface-container text-on-surface-variant text-xs font-medium">
                          {averageJobDurationSeconds !== null ? formatJobDuration(averageJobDurationSeconds) : '—'}
                        </Badge>
                      </div>
                      {currentSession.savedData.length > 0 && (
                        <Badge className="bg-session-complete text-white">Saved: {currentSession.savedData.length}</Badge>
                      )}
                    </div>
                  </div>

                  {/* Text Editor Cards */}
                  <div className="space-y-card-gap">
                    {/* Source Text Card */}
                    <Card className="bg-surface border border-outline-variant shadow-none">
                      <CardHeader className="pb-3">
                        <div className="flex items-center justify-between">
                          <CardTitle className="text-label-caps tracking-wider text-on-surface-variant uppercase">
                            SOURCE TEXT (原文)
                          </CardTitle>
                          <button
                            onClick={() => currentSession?.originalText && copyToClipboard(currentSession.originalText, "原文がクリップボードにコピーされました")}
                            className="p-1.5 rounded hover:bg-surface-container transition-colors"
                            title="コピー"
                          >
                            <span className="material-symbols-outlined md-18 text-on-surface-variant">content_copy</span>
                          </button>
                        </div>
                      </CardHeader>
                      <CardContent>
                        <HighlightedTextarea
                          placeholder="原文テキストをここに貼り付けてください..."
                          value={currentSession.originalText}
                          onChange={(e) => updateCurrentSession({ originalText: e.target.value })}
                          className="min-h-[180px] text-body-base leading-relaxed bg-surface-container border-outline-variant"
                          highlights={sourceHighlights}
                        />
                      </CardContent>
                    </Card>

                    {/* Exemplar Text Card (optional 模範回答訳文) */}
                    <ExemplarTextCard
                      value={currentSession.exemplarTranslation}
                      onChange={(value) => updateCurrentSession({ exemplarTranslation: value })}
                      onCopy={(value) =>
                        copyToClipboard(value, "模範回答訳文がクリップボードにコピーされました")
                      }
                      open={isExemplarCardOpen}
                      onOpenChange={handleExemplarCardOpenChange}
                    />

                    {/* Target Text Card */}
                    <Card className="bg-surface border border-outline-variant shadow-none">
                      <CardHeader className="pb-3">
                        <div className="flex items-center justify-between">
                          <CardTitle className="text-label-caps tracking-wider text-on-surface-variant uppercase">
                            TARGET TEXT (翻訳/編集)
                          </CardTitle>
                          <button
                            onClick={() => currentSession?.targetText && copyToClipboard(currentSession.targetText, "添削対象テキストがクリップボードにコピーされました")}
                            className="p-1.5 rounded hover:bg-surface-container transition-colors"
                            title="コピー"
                          >
                            <span className="material-symbols-outlined md-18 text-on-surface-variant">content_copy</span>
                          </button>
                        </div>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <HighlightedTextarea
                          placeholder="添削対象テキストをここに貼り付けてください..."
                          value={currentSession.targetText}
                          onChange={(e) => updateCurrentSession({ targetText: e.target.value })}
                          onSelect={handleTargetTextSelect}
                          className="min-h-[200px] text-body-base leading-relaxed bg-surface-container border-outline-variant"
                          highlights={targetHighlights}
                        />
                        
                        {/* Offline mode toggle */}
                        <div className="flex items-center justify-between p-3 bg-surface-container border border-outline-variant rounded-lg">
                          <div className="flex items-center gap-2">
                            <Checkbox
                              id="offline-mode"
                              checked={offlineMode}
                              onCheckedChange={(checked) => setOfflineMode(checked === true)}
                              disabled={webgpuSupported === false}
                            />
                            <Label htmlFor="offline-mode" className="text-body-sm text-on-surface cursor-pointer">
                              オフラインモード（WebLLM）
                            </Label>
                          </div>
                          {lastSuggestionSource && (
                            <Badge variant={lastSuggestionSource === "api" ? "default" : "secondary"} className="text-xs">
                              {lastSuggestionSource === "api" ? "クラウドAPI" : "ローカルAI"}
                            </Badge>
                          )}
                        </div>
                        
                        {/* WebGPU unsupported message */}
                        {webgpuSupported === false && (
                          <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-body-sm text-yellow-800">
                            <p className="font-medium">オフラインモード利用不可</p>
                            <p className="text-metadata mt-1">{webgpuUnsupportedReason}</p>
                            <p className="text-metadata mt-1">クラウドAPIが利用できない場合、</p>
                            <p className="text-metadata">AI提案機能を利用できません</p>
                            <p className="text-metadata mt-1">手動でカスタム修正を追加してください。</p>
                          </div>
                        )}
                        
                        {/* AI Diagnostics Panel */}
                        {(webllmStatus.state === "loading" || 
                          webllmStatus.state === "generating" || 
                          webllmStatus.state === "checking_webgpu" ||
                          webllmStatus.state === "error") && (
                          <AIDiagnosticsPanel status={webllmStatus} />
                        )}
                        
                        {/* Generate Button */}
                        <div className="flex justify-center">
                          <Button
                            onClick={handleGenerateClick}
                            disabled={
                              !currentSession.targetText.trim() ||
                              !currentSession.originalText.trim() ||
                              (offlineMode && webgpuSupported === false)
                            }
                            className="bg-on-surface text-surface hover:bg-on-surface/90 rounded-full px-6 py-2"
                          >
                            {(() => {
                              const processingCount = jobQueue.filter(j => j.status === 'processing').length
                              const queuedCount = jobQueue.filter(j => j.status === 'queued').length
                              
                              return (
                                <>
                                  <span className="material-symbols-outlined md-18 mr-2">auto_awesome</span>
                                  Generate AI Suggestions
                                  {(processingCount > 0 || queuedCount > 0) && (
                                    <Badge variant="secondary" className="ml-2 text-xs bg-surface-container text-on-surface">
                                      {processingCount > 0 && `${processingCount}`}
                                      {processingCount > 0 && queuedCount > 0 && '/'}
                                      {queuedCount > 0 && `${queuedCount}`}
                                    </Badge>
                                  )}
                                  {offlineMode && !isEngineReady() && (
                                    <span className="ml-1 text-metadata">（初回DL）</span>
                                  )}
                                </>
                              )
                            })()}
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  </div>

                </div>
              )}
            </main>

            {/* Resize Handle (Desktop only) */}
            <div
              className={`hidden lg:flex items-center justify-center w-1.5 cursor-col-resize hover:bg-md3-primary/30 transition-colors flex-shrink-0 ${isResizing ? 'bg-md3-primary/50' : 'bg-transparent hover:bg-outline-variant/50'}`}
              onPointerDown={handleResizeStart}
              title="ドラッグしてリサイズ"
            >
              <div className="w-0.5 h-16 bg-outline-variant/60 rounded-full" />
            </div>

            {/* Right Pane - Job Queue + Suggestions (Desktop: side panel with resizable width, Mobile: below editor) */}
            <aside 
              className="w-full lg:flex-shrink-0 bg-surface border-t lg:border-t-0 border-outline-variant overflow-y-auto"
              style={isLgScreen ? { width: rightPaneWidth } : undefined}
            >
              <div className="p-4 lg:p-6 space-y-card-gap">
                {/* Job Queue Panel */}
                {jobQueue.length > 0 && (
                  <Card className="bg-surface border border-outline-variant shadow-none">
                    <CardHeader className="pb-3">
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-label-caps tracking-wider text-on-surface-variant uppercase">
                          Job Queue
                        </CardTitle>
                        <Badge className="bg-session-active text-white text-xs font-semibold">
                          {activeJobCount} Active
                        </Badge>
                      </div>
                      <CardDescription className="text-metadata text-on-surface-variant mt-1">
                        {offlineMode 
                          ? "WebLLMモード: 逐次処理（1件ずつ）" 
                          : `APIモード: 並列処理（最大${MAX_CONCURRENT_API_JOBS}件同時）`}
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      {/* 縦積みではなく横スライド。ジョブが何件積まれてもパネルの
                          高さは一定で、下のAI Suggestions/Historyを押し下げない
                          （slide-job-queue-carousel change参照）。 */}
                      <JobQueueCarousel
                        items={orderedJobQueue}
                        getKey={(job) => job.id}
                        ariaLabel="ジョブキュー一覧（横スライド）"
                        renderItem={(job) => {
                          const isClickable = job.status === 'completed' && job.suggestions
                          return (
                            <div
                              className={`h-full flex flex-col border rounded-lg p-3 transition-colors ${
                                job.status === 'processing' 
                                  ? 'bg-primary-container border-md3-primary' 
                                  : job.status === 'completed'
                                  ? 'bg-green-50 border-session-complete'
                                  : job.status === 'failed'
                                  ? 'bg-red-50 border-error'
                                  : 'bg-surface-container border-outline-variant'
                              } ${isClickable ? 'cursor-pointer hover:bg-green-100' : ''}`}
                              onClick={isClickable ? () => confirmJob(job) : undefined}
                              onKeyDown={isClickable ? (e) => {
                                if (e.key === 'Enter' || e.key === ' ') {
                                  e.preventDefault()
                                  confirmJob(job)
                                }
                              } : undefined}
                              role={isClickable ? 'button' : undefined}
                              tabIndex={isClickable ? 0 : undefined}
                            >
                              <div className="flex items-center gap-2 flex-wrap">
                                {job.status === 'processing' && (
                                  <span className="material-symbols-outlined md-18 animate-spin text-md3-primary">progress_activity</span>
                                )}
                                {job.status === 'completed' && (
                                  <span className="material-symbols-outlined md-18 text-session-complete">check_circle</span>
                                )}
                                {job.status === 'failed' && (
                                  <span className="material-symbols-outlined md-18 text-error">error</span>
                                )}
                                {job.status === 'queued' && (
                                  <span className="material-symbols-outlined md-18 text-on-surface-variant">schedule</span>
                                )}
                                <Badge variant={
                                  job.status === 'processing' ? 'default' :
                                  job.status === 'completed' ? 'outline' :
                                  job.status === 'failed' ? 'destructive' : 'secondary'
                                } className="text-xs">
                                  {job.status === 'processing' ? '処理中' :
                                   job.status === 'completed' ? '完了' :
                                   job.status === 'failed' ? '失敗' : '待機中'}
                                </Badge>
                                {job.source && (
                                  <Badge variant="outline" className="text-xs">
                                    {job.source === 'api' ? 'API' : 'WebLLM'}
                                  </Badge>
                                )}
                              </div>
                              <p className="text-metadata text-on-surface-variant mt-1 truncate">
                                {deriveCorrectionLabel(job).text}
                              </p>
                              <p className="text-metadata text-on-surface-variant">
                                {job.queuedAt.toLocaleTimeString()}
                                {job.completedAt && ` → ${job.completedAt.toLocaleTimeString()}`}
                              </p>
                              {job.error && (
                                // Cloud failures carry a per-provider breakdown on a
                                // second line; keep it readable here and in full on hover.
                                <p
                                  className="text-metadata text-error mt-1 line-clamp-3 whitespace-pre-line"
                                  title={job.error}
                                >
                                  {job.error}
                                </p>
                              )}
                              {isClickable && (
                                <div className="mt-2 flex items-center text-body-sm text-session-complete font-medium">
                                  <span className="material-symbols-outlined md-18 mr-1">check_circle</span>
                                  確認
                                </div>
                              )}
                              {job.status === 'failed' && (
                                <Button
                                  variant="outline"
                                  size="sm"
                                  className="mt-2 h-8 px-2 border-error text-error hover:bg-red-100 self-start"
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    retryJob(job)
                                  }}
                                >
                                  <span className="material-symbols-outlined md-18 mr-1">refresh</span>
                                  再試行
                                </Button>
                              )}
                            </div>
                          )
                        }}
                      />
                    </CardContent>
                  </Card>
                )}

                {/* AI Suggestions Panel */}
                {currentSession && currentSession.suggestions.length > 0 && (
                  <Card data-suggestions-card className="bg-surface border border-outline-variant shadow-none">
                    <CardHeader className="pb-3">
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-label-caps tracking-wider text-on-surface-variant uppercase">
                          AI Suggestions
                          {confirmingJobId && (
                            <span className="ml-2 text-session-active normal-case">• Reviewing</span>
                          )}
                        </CardTitle>
                        <span className="text-metadata text-on-surface-variant">
                          {currentSession.suggestions.length} Results
                        </span>
                      </div>
                      <CardDescription className="text-metadata text-on-surface-variant mt-1">
                        Select 3+ to save
                      </CardDescription>
                      {/* Which model wrote these suggestions. Its own line so a
                          long model id wraps instead of pushing the count and
                          selection badges around. */}
                      {lastSuggestionModel && (
                        <p
                          data-testid="suggestion-model-caption"
                          className="text-metadata text-on-surface-variant/80 mt-1 break-all"
                        >
                          {lastSuggestionModel} used
                        </p>
                      )}
                      <div className="flex items-center gap-2 flex-wrap mt-2">
                        <Badge className={canSave ? "bg-session-complete text-white" : "bg-surface-container text-on-surface-variant"}>
                          選択済み: {selectedCount}/3+
                        </Badge>
                        {canSave && (
                          <Badge className="bg-session-complete text-white text-xs">
                            保存可能
                          </Badge>
                        )}
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      {currentSession.suggestions.map((suggestion, index) => (
                        <div
                          key={suggestion.id}
                          onDoubleClick={() => toggleSuggestionSelection(suggestion.id)}
                          onMouseEnter={() => setHoveredSuggestionId(suggestion.id)}
                          onMouseLeave={() => setHoveredSuggestionId((current) => (current === suggestion.id ? null : current))}
                          className={`group border rounded-lg p-3 transition-colors cursor-pointer select-none ${
                            suggestion.selected
                              ? 'bg-primary-container border-md3-primary'
                              : 'border-outline-variant hover:bg-surface-container'
                          }`}
                          title="ダブルクリックで選択/選択解除"
                        >
                          <div className="flex-1 min-w-0 space-y-2">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                <span className="text-label-caps text-on-surface-variant uppercase">
                                  Option {String.fromCharCode(65 + index)}
                                  {suggestion.isCustom && ' (カスタム)'}
                                </span>
                                {suggestion.selected && suggestion.selectedOrder && (
                                  <Badge variant="outline" className="text-xs px-1 py-0">
                                    {suggestion.selectedOrder}
                                  </Badge>
                                )}
                              </div>
                              {/* Hover-reveal action icons */}
                              <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    copyToClipboard(`${suggestion.original}\n${suggestion.reason}`, "提案内容がクリップボードにコピーされました")
                                  }}
                                  className="p-1 rounded hover:bg-surface-container-high"
                                  title="コピー"
                                >
                                  <span className="material-symbols-outlined md-18 text-on-surface-variant">content_copy</span>
                                </button>
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    toggleSuggestionSelection(suggestion.id)
                                  }}
                                  className="p-1 rounded hover:bg-surface-container-high"
                                  title={suggestion.selected ? "選択解除" : "選択"}
                                >
                                  <span className={`material-symbols-outlined md-18 ${suggestion.selected ? 'text-session-complete' : 'text-on-surface-variant'}`}>
                                    {suggestion.selected ? 'check_circle' : 'radio_button_unchecked'}
                                  </span>
                                </button>
                              </div>
                            </div>
                            {/* Pointed text */}
                            <div className="bg-red-50 p-2 rounded border border-red-200">
                              <Label className="text-metadata font-medium text-red-600">指摘箇所</Label>
                              <p className="text-body-sm text-red-800 mt-1">{suggestion.original}</p>
                            </div>
                            {/* Reason */}
                            <div className="bg-primary-container/50 p-2 rounded">
                              <Label className="text-metadata font-medium text-md3-primary">修正コメント</Label>
                              {suggestion.selected ? (
                                <Textarea
                                  ref={(el) => {
                                    suggestionTextareaRefs.current[suggestion.id] = el
                                    resizeSuggestionTextarea(el)
                                  }}
                                  value={suggestion.userModifiedReason || suggestion.reason}
                                  onChange={(e) => {
                                    updateSuggestionReason(suggestion.id, e.target.value)
                                    resizeSuggestionTextarea(e.target)
                                  }}
                                  onDoubleClick={(e) => e.stopPropagation()}
                                  className="text-body-sm min-h-[2.5rem] mt-1 bg-surface border-outline-variant resize-none overflow-hidden"
                                />
                              ) : (
                                <p className="text-body-sm text-on-surface mt-1">{suggestion.reason}</p>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}

                      {/* Custom Correction Form */}
                      {showCustomForm && (
                        <div className="border-2 border-dashed border-outline rounded-lg p-3 space-y-3 bg-surface-container">
                          <div className="flex items-center gap-2">
                            <span className="material-symbols-outlined md-18 text-on-surface-variant">add</span>
                            <Label className="text-body-sm font-medium text-on-surface">修正内容を追加</Label>
                          </div>
                          <div>
                            <Label htmlFor="custom-original" className="text-metadata font-medium text-red-600">
                              修正前のテキスト
                            </Label>
                            <Input
                              id="custom-original"
                              value={customCorrection.original}
                              onChange={(e) =>
                                setCustomCorrection((prev) => ({ ...prev, original: e.target.value }))
                              }
                              placeholder="修正前のテキストを入力"
                              className="mt-1 bg-surface border-outline-variant"
                            />
                          </div>
                          <div>
                            <Label htmlFor="custom-reason" className="text-metadata font-medium text-md3-primary">
                              修正コメント
                            </Label>
                            <Textarea
                              id="custom-reason"
                              value={customCorrection.reason}
                              onChange={(e) =>
                                setCustomCorrection((prev) => ({ ...prev, reason: e.target.value }))
                              }
                              placeholder="修正コメントを入力"
                              className="min-h-[60px] mt-1 bg-surface border-outline-variant"
                            />
                          </div>
                          <Button onClick={addCustomCorrection} size="sm" className="w-full bg-md3-primary text-on-primary">
                            <span className="material-symbols-outlined md-18 mr-1">add</span>
                            修正内容を追加
                          </Button>
                        </div>
                      )}

                      {/* Overall Comment */}
                      {currentSession.overallComment && (
                        <div className="border rounded-lg p-3 bg-primary-container/30 border-md3-primary/30">
                          <div className="flex items-center gap-2 mb-2">
                            <span className="material-symbols-outlined md-18 text-md3-primary">chat</span>
                            <Label className="text-body-sm font-medium text-on-primary-container">全体総括コメント</Label>
                          </div>
                          <Textarea
                            value={currentSession.overallComment}
                            onChange={(e) => updateCurrentSession({ overallComment: e.target.value })}
                            className="min-h-[80px] bg-surface border-outline-variant"
                            placeholder="全体的な総括コメントを入力してください..."
                          />
                        </div>
                      )}

                      <Separator className="bg-outline-variant" />

                      <Button
                        onClick={saveCorrections}
                        disabled={!canSave || isSaving}
                        className="w-full bg-md3-primary text-on-primary hover:bg-md3-primary/90"
                        size="lg"
                      >
                        <span
                          className={`material-symbols-outlined md-18 mr-2${isSaving ? " animate-spin" : ""}`}
                        >
                          {isSaving ? "progress_activity" : "content_copy"}
                        </span>
                        {isSaving ? "保存中..." : `確定してコピー・保存 (${selectedCount}/3)`}
                      </Button>
                    </CardContent>
                  </Card>
                )}

                {/* Execution History */}
                {currentSession && currentSession.savedData.length > 0 && (
                  <Card className="bg-surface border border-outline-variant shadow-none">
                    <CardHeader className="pb-3">
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-label-caps tracking-wider text-on-surface-variant uppercase">
                          History
                        </CardTitle>
                        <span className="text-metadata text-on-surface-variant">
                          {currentSession.savedData.length} saved
                        </span>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        {currentSession.savedData.map((data, index) => {
                          const handleRestore = () => {
                            restoreFromHistory(data)
                            setConfirmingHistoryIndex(index)
                          }
                          return (
                          <div 
                            key={index} 
                            className={`border rounded-lg p-3 transition-colors cursor-pointer ${
                              data.confirmed 
                                ? 'bg-green-50 border-session-complete hover:bg-green-100' 
                                : 'bg-surface-container border-outline-variant hover:border-md3-primary'
                            }`}
                            onClick={handleRestore}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter' || e.key === ' ') {
                                e.preventDefault()
                                handleRestore()
                              }
                            }}
                            role="button"
                            tabIndex={0}
                          >
                            <div className="flex justify-between items-start gap-2">
                              {/* 見出しは中身から導いたラベル。連番だけでは
                                  どのラウンドか判別できなかったため主従を入れ替え、
                                  #N は日時と同じメタデータ行へ降ろした
                                  （identifiable-history-card-headings change参照）。 */}
                              <div className="min-w-0 flex-1">
                                <div className="flex items-center gap-2">
                                  <h4 className="font-semibold text-body-sm text-on-surface truncate">
                                    {deriveCorrectionLabel(data).text}
                                  </h4>
                                  {data.confirmed ? (
                                    <Badge className="bg-session-complete text-white text-xs font-medium shrink-0">
                                      Saved
                                    </Badge>
                                  ) : (
                                    <Badge variant="outline" className="text-on-surface-variant border-outline text-xs font-medium shrink-0">
                                      未確認
                                    </Badge>
                                  )}
                                </div>
                                <p className="text-metadata text-on-surface-variant">
                                  #{index + 1} · {data.timestamp.toLocaleString()}
                                </p>
                              </div>
                              <div className="flex gap-1 shrink-0">
                                <Button 
                                  variant={data.confirmed ? "ghost" : "outline"} 
                                  size="sm"
                                  className="h-8 px-2"
                                  title="確認"
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    handleRestore()
                                  }}
                                >
                                  <span className={`material-symbols-outlined md-18 ${data.confirmed ? 'text-session-complete' : ''}`}>
                                    check_circle
                                  </span>
                                </Button>
                                <Button
                                  variant="outline"
                                  size="sm"
                                  className="h-8 px-2"
                                  title="アーカイブ"
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    archiveHistoryRound(data, index)
                                  }}
                                >
                                  <span className="material-symbols-outlined md-18 text-on-surface-variant">archive</span>
                                </Button>
                              </div>
                            </div>
                          </div>
                          )
                        })}
                      </div>
                    </CardContent>
                  </Card>
                )}
              </div>
            </aside>
          </div>
        </div>
      )}

      {/* Shared prompt editor. Mounted outside the workspace tree so opening or
          closing it cannot touch session state, drafts, or the job queue. */}
      <PromptSettingsDialog
        open={promptSettingsOpen}
        onOpenChange={setPromptSettingsOpen}
        onSaved={(description) => toast({ title: "設定", description })}
      />
    </div>
  )
}
