"use client"

import { useEffect, useCallback } from "react"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Checkbox } from "@/components/ui/checkbox"
import { Separator } from "@/components/ui/separator"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet"
import { Input } from "@/components/ui/input"
import {
  FileText,
  Bot,
  Plus,
  Menu,
  Trash2,
  Calendar,
  Loader2,
  Copy,
  CheckCircle,
  MessageSquare,
  LogOut,
} from "lucide-react"
import { useToast } from "@/hooks/use-toast"
import { sessionAPI, historyAPI, proposalAPI, suggestionsAPI } from "./api"
import { useAuth } from "./auth-provider"
import { LoginScreen } from "./login-screen"
import {
  generateSuggestions as generateWebLLMSuggestions,
  checkWebGPUSupport,
  isEngineReady,
  WEBLLM_MODEL_DISPLAY_NAME,
  formatElapsedTime,
  formatDownloadProgress,
  PHASE_LABELS,
  getDiagnosticsTracker,
  type EngineStatus,
} from "@/lib/webllm"

type CorrectionSuggestion = {
  id: string
  original: string
  reason: string
  selected: boolean
  selectedOrder?: number
  userModifiedReason?: string
  isCustom?: boolean
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
}

type QueuedJob = {
  id: string
  targetText: string
  status: 'queued' | 'processing' | 'completed' | 'failed'
  suggestions?: CorrectionSuggestion[]
  overallComment?: string
  error?: string
  queuedAt: Date
  completedAt?: Date
  source?: 'api' | 'webllm'
}

const MAX_CONCURRENT_API_JOBS = 30
const MAX_CONCURRENT_WEBLLM_JOBS = 1

type Session = {
  id: string
  name: string
  createdAt: Date
  correctionCount: number
  originalText: string
  targetText: string
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
  isSelected: number
  selectedOrder?: number
  isModified: number
  modifiedReason?: string
  isCustom: number
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
    : "bg-blue-50 border-blue-200"
  const textClass = status.state === "error"
    ? "text-red-800"
    : "text-blue-800"
  const textMutedClass = status.state === "error"
    ? "text-red-700"
    : "text-blue-700"
  const progressBgClass = status.state === "error"
    ? "bg-red-200"
    : "bg-blue-200"
  const progressFgClass = status.state === "error"
    ? "bg-red-600"
    : "bg-blue-600"

  return (
    <div className={`p-3 border rounded-lg ${bgClass}`}>
      {/* Header: Model info + current phase */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Loader2 className={`w-4 h-4 animate-spin ${textClass}`} />
          <span className={`text-sm font-medium ${textClass}`}>
            {diagnostics?.phaseLabel || (status.state === "loading" ? "準備中" : status.state === "generating" ? "分析中" : "処理中")}
          </span>
        </div>
        <div className="flex items-center gap-2 text-xs">
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
          <p className={`text-xs ${textMutedClass}`}>
            {status.text || formatDownloadProgress(status.progress)}
          </p>
        </>
      )}
      
      {/* Timing info */}
      {diagnostics && (
        <div className={`flex gap-4 text-xs ${textMutedClass} mt-2`}>
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
        <div className="mt-2 p-2 bg-red-100 rounded text-xs text-red-800">
          <strong>タイムアウト:</strong> {PHASE_LABELS[diagnostics.timeoutPhase]} フェーズでタイムアウトしました
        </div>
      )}
      
      {/* Error message - only show if NOT a timeout (timeoutPhase already shows the info) */}
      {status.state === "error" && !diagnostics?.timeoutPhase && (
        <div className="mt-2 p-2 bg-red-100 rounded text-xs text-red-800">
          <strong>エラー:</strong> {"error" in status ? status.error : "不明なエラー"}
        </div>
      )}
      
      {/* DevTools hint (only in development) */}
      {process.env.NODE_ENV === "development" && (
        <p className={`text-xs ${textMutedClass} mt-2 opacity-60`}>
          DevTools: window.__webllmDiagnostics.getState()
        </p>
      )}
    </div>
  )
}

export default function TextCorrectionApp() {
  const { session, isLoading: isAuthLoading, signOut } = useAuth()
  const [sessions, setSessions] = useState<Session[]>([])
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [desktopSidebarOpen, setDesktopSidebarOpen] = useState(true) // 新しく追加
  const [customCorrection, setCustomCorrection] = useState({ original: "", reason: "" })
  const [showCustomForm, setShowCustomForm] = useState(false)
  const [selectionCounter, setSelectionCounter] = useState(0)
  const [webllmStatus, setWebllmStatus] = useState<EngineStatus>({ state: "idle" })
  const [webgpuSupported, setWebgpuSupported] = useState<boolean | null>(null)
  const [webgpuUnsupportedReason, setWebgpuUnsupportedReason] = useState<string | null>(null)
  const [offlineMode, setOfflineMode] = useState(false)
  const [lastSuggestionSource] = useState<"api" | "webllm" | null>(null)
  const [jobQueue, setJobQueue] = useState<QueuedJob[]>([])
  const [confirmingHistoryIndex, setConfirmingHistoryIndex] = useState<number | null>(null)
  const { toast } = useToast()

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

  // 単一ジョブを非同期処理する関数（並列実行可能）
  const processJobAsync = useCallback(async (jobId: string, targetText: string, originalText: string) => {
    // ジョブをprocessingに更新
    setJobQueue(prev => prev.map(j => 
      j.id === jobId ? { ...j, status: 'processing' as const } : j
    ))

    toast({
      title: "処理開始",
      description: `ジョブ ${jobId.slice(-4)} を処理中...`,
    })

    try {
      let suggestions: CorrectionSuggestion[] = []
      let overallComment = ''
      let source: 'api' | 'webllm' = 'api'

      if (offlineMode) {
        // WebLLMモード
        source = 'webllm'
        if (!webgpuSupported) {
          throw new Error(webgpuUnsupportedReason || "WebGPU非対応")
        }
        
        const data = await generateWebLLMSuggestions(
          { originalText, targetText, instructionPrompt: "CCTalkからの添削指示" },
          (status) => setWebllmStatus(status)
        )
        suggestions = data.suggestions.map(s => ({ ...s, selected: false }))
        overallComment = data.overallComment
      } else {
        // APIモード（並列実行可能）
        try {
          const data = await suggestionsAPI.generate(originalText, targetText)
          console.log("[processJobAsync] API response received:", {
            suggestionsCount: data.suggestions?.length ?? 0,
            suggestions: data.suggestions,
            overallComment: data.overallComment?.substring(0, 100),
          })
          suggestions = data.suggestions.map(s => ({ ...s, selected: false }))
          overallComment = data.overallComment
          source = 'api'
        } catch (apiError) {
          console.warn("[suggestions] API failed, falling back to WebLLM:", apiError)
          
          if (!webgpuSupported) {
            throw new Error("クラウドAPIに接続できませんでした。WebGPUも非対応のため、AI提案機能を利用できません。")
          }

          // WebLLMフォールバックをユーザーに通知
          toast({
            title: "APIエラー",
            description: "クラウドAPIに接続できませんでした。ローカルAI（WebLLM）にフォールバックします。",
          })

          // WebLLMにフォールバック
          source = 'webllm'
          const data = await generateWebLLMSuggestions(
            { originalText, targetText, instructionPrompt: "CCTalkからの添削指示" },
            (status) => setWebllmStatus(status)
          )
          suggestions = data.suggestions.map(s => ({ ...s, selected: false }))
          overallComment = data.overallComment
        }
      }

      // ジョブを完了に更新
      setJobQueue(prev => prev.map(j => 
        j.id === jobId 
          ? { 
              ...j, 
              status: 'completed' as const, 
              suggestions,
              overallComment,
              source,
              completedAt: new Date() 
            } 
          : j
      ))

      toast({
        title: "完了",
        description: `ジョブ ${jobId.slice(-4)} が完了しました`,
      })

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
      targetText,
      status: 'queued',
      queuedAt: new Date(),
    }
    
    setJobQueue(prev => [...prev, newJob])
    
    // 即座にジョブ処理を開始（並列処理対応）
    const processingCount = jobQueue.filter(j => j.status === 'processing').length
    const maxConcurrent = offlineMode ? MAX_CONCURRENT_WEBLLM_JOBS : MAX_CONCURRENT_API_JOBS
    
    if (processingCount < maxConcurrent) {
      // スロットが空いているので即座に処理開始
      processJobAsync(newJob.id, targetText, currentSession.originalText)
    }
    
    toast({
      title: "キューに追加",
      description: `ジョブをキューに追加しました`,
    })
    
    return true
  }, [jobQueue, currentSession, offlineMode, processJobAsync, toast])

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
      processJobAsync(job.id, job.targetText, currentSession.originalText)
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
  const handleGenerateClick = useCallback(() => {
    if (!currentSession?.targetText.trim()) return
    
    addJobAndProcess(currentSession.targetText)
    // テキストエリアをクリアして次の入力を待つ
    updateCurrentSession({ targetText: "" })
  }, [currentSession, addJobAndProcess, updateCurrentSession])

  // セッション詳細をオンデマンドで取得
  const loadSessionDetails = useCallback(async (sessionId: string) => {
    try {
      console.log("Loading session details for:", sessionId)
      const historiesData = await historyAPI.getHistories(sessionId)
      console.log("Histories for session", sessionId, ":", historiesData)

      const savedData: SavedData[] = []
      for (const history of historiesData) {
        const proposalsData: ProposalAPIResponse[] = await proposalAPI.getProposals(history.historyId)
        const aiSuggestions: CorrectionSuggestion[] = proposalsData.map((proposal) => ({
          id: proposal.proposalId,
          original: proposal.originalAfterText,
          reason: proposal.originalReason || "",
          selected: proposal.isSelected === 1,
          selectedOrder: proposal.selectedOrder,
          userModifiedReason: proposal.modifiedReason,
          isCustom: proposal.isCustom === 1,
        }))

        savedData.push({
          originalText: history.originalText,
          instructionPrompt: history.instructionPrompt,
          targetText: history.targetText,
          aiSuggestions,
          selectedCorrections: aiSuggestions.filter((s) => s.selected),
          overallComment: history.combinedComment,
          combinedComment: history.combinedComment,
          timestamp: new Date(history.timestamp),
        })
      }

      setSessions((prevSessions) =>
        prevSessions.map((s) =>
          s.id === sessionId ? { ...s, savedData } : s
        ),
      )
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
    
    setCurrentSessionId(sessionId)
    setSidebarOpen(false)
    loadSessionDetails(sessionId)
  }, [jobQueue, loadSessionDetails])

  // 確認中のジョブID（ジョブキューからの確認用）
  const [confirmingJobId, setConfirmingJobId] = useState<string | null>(null)

  // Reactive scroll to suggestions card when confirming from job queue
  // This replaces the setTimeout-based scroll in confirmJob for reliability
  useEffect(() => {
    // Only scroll when confirming from job queue and suggestions are loaded
    if (confirmingJobId && currentSession?.suggestions && currentSession.suggestions.length > 0) {
      // Small delay to ensure DOM is updated after React render
      const timeoutId = setTimeout(() => {
        const suggestionsCard = document.querySelector('[data-suggestions-card]')
        if (suggestionsCard) {
          suggestionsCard.scrollIntoView({ behavior: 'smooth', block: 'start' })
        }
      }, 50)
      return () => clearTimeout(timeoutId)
    }
  }, [confirmingJobId, currentSession?.suggestions])

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
    
    // ジョブの結果を現在のセッションにロード
    updateCurrentSession({
      targetText: job.targetText,
      suggestions: job.suggestions,
      overallComment: job.overallComment || '',
    })
    
    setShowCustomForm(true)
    setSelectionCounter(0)
    
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
  const loadSessions = useCallback(async () => {
    try {
      console.log("Loading sessions...")
      const sessionsData: SessionAPIResponse[] = await sessionAPI.getSessions()
      console.log("Sessions data received:", sessionsData)

      // APIから取得したデータをフロントエンドのSession型に変換
      const convertedSessions: Session[] = sessionsData.map((s) => ({
        id: s.sessionId,
        name: s.name,
        createdAt: new Date(s.createdAt),
        correctionCount: s.correctionCount, // 保存済み件数を追加
        originalText: "",
        targetText: "",
        suggestions: [],
        overallComment: "",
        savedData: [],
      }))

      setSessions(convertedSessions)
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
    } catch (error) {
      console.error("Failed to delete session:", error)
      toast({
        title: "エラー",
        description: "セッションの削除に失敗しました",
        variant: "destructive",
      })
    }
  }

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

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      toast({
        title: "コピー完了",
        description: "修正内容がクリップボードにコピーされました",
      })
    } catch {
      toast({
        title: "コピー失敗",
        description: "クリップボードへのコピーに失敗しました",
        variant: "destructive",
      })
    }
  }

  // 履歴をAPIに保存
  const saveCorrections = async () => {
    if (!currentSession) return

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

    try {
      // 履歴データを作成
      const historyData = {
        sessionId: currentSession.id,
        originalText: currentSession.originalText,
        targetText: currentSession.targetText,
        instructionPrompt: "CCTalkからの添削指示",
        combinedComment: currentSession.overallComment,
        selectedProposalIds: JSON.stringify(selectedSuggestions.map((s) => s.id)),
        customProposals: JSON.stringify(selectedSuggestions.filter((s) => s.isCustom)),
      }

      // 履歴をAPIに保存
      const savedHistory = await historyAPI.createHistory(historyData)

      // すべての提案をAPIに保存（選択されたものも選択されていないものも）
      for (const suggestion of currentSession.suggestions) {
        const proposalData = {
          historyId: savedHistory.historyId,
          type: (suggestion.isCustom ? "Custom" : "AI") as "AI" | "Custom",
          originalAfterText: suggestion.original,
          originalReason: suggestion.reason,
          modifiedAfterText: suggestion.userModifiedReason ? suggestion.original : suggestion.original,
          modifiedReason: suggestion.userModifiedReason || suggestion.reason,
          isSelected: suggestion.selected ? 1 : 0,
          isModified: suggestion.userModifiedReason ? 1 : 0,
          isCustom: suggestion.isCustom ? 1 : 0,
          selectedOrder: suggestion.selected ? suggestion.selectedOrder : undefined,
        }
        await proposalAPI.createProposal(proposalData)
      }

      // クリップボードにコピー
      const numberedCorrections = selectedSuggestions
        .map((suggestion, index) => {
          const reasonText = suggestion.userModifiedReason || suggestion.reason
          return `${index + 1}.${suggestion.original}\n${reasonText}`
        })
        .join("\n\n")

      const combinedComment = `${numberedCorrections}\n\n${currentSession.overallComment}`
      await copyToClipboard(combinedComment)

      // フロントエンドの状態を更新
      if (confirmingJobId !== null) {
        // ジョブキューからの確認フロー: ジョブを完了済みとしてマーク、履歴に保存
        const savedData: SavedData = {
          originalText: currentSession.originalText,
          instructionPrompt: "CCTalkからの添削指示",
          targetText: currentSession.targetText,
          aiSuggestions: currentSession.suggestions,
          selectedCorrections: selectedSuggestions,
          overallComment: currentSession.overallComment,
          combinedComment,
          timestamp: new Date(),
          confirmed: true,
        }

        updateCurrentSession({
          savedData: [...currentSession.savedData, savedData],
          targetText: "",
          suggestions: [],
          overallComment: "",
        })
        
        // 確認済みジョブをキューから削除
        setJobQueue(prev => prev.filter(j => j.id !== confirmingJobId))
        setConfirmingJobId(null)
        
        toast({
          title: "確認完了",
          description: "ジョブを確認済みにしました。クリップボードにコピーしました。",
        })
      } else if (confirmingHistoryIndex !== null) {
        // 実行履歴からの確認フロー: 既存の履歴を確認済みにマーク
        const updatedSavedData = currentSession.savedData.map((data, idx) => 
          idx === confirmingHistoryIndex ? { ...data, confirmed: true } : data
        )
        updateCurrentSession({
          savedData: updatedSavedData,
          targetText: "",
          suggestions: [],
          overallComment: "",
        })
        setConfirmingHistoryIndex(null)
        toast({
          title: "確認完了",
          description: "履歴を確認済みにしました。クリップボードにコピーしました。",
        })
      } else {
        // 新規保存フロー
        const savedData: SavedData = {
          originalText: currentSession.originalText,
          instructionPrompt: "CCTalkからの添削指示",
          targetText: currentSession.targetText,
          aiSuggestions: currentSession.suggestions,
          selectedCorrections: selectedSuggestions,
          overallComment: currentSession.overallComment,
          combinedComment,
          timestamp: new Date(),
          confirmed: true,
        }

        updateCurrentSession({
          savedData: [...currentSession.savedData, savedData],
          targetText: "",
          suggestions: [],
          overallComment: "",
        })
        
        toast({
          title: "保存完了",
          description: "修正内容が保存され、クリップボードにコピーされました",
        })
      }

      setShowCustomForm(false)
      setCustomCorrection({ original: "", reason: "" })
      setSelectionCounter(0)
    } catch (error) {
      console.error("Failed to save corrections:", error)
      toast({
        title: "エラー",
        description: "修正内容の保存に失敗しました",
        variant: "destructive",
      })
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

    setShowCustomForm(true)

    toast({
      title: "確認中",
      description: "履歴データをロードしました。内容を確認して「確定してコピー・保存」を実行してください。",
    })
  }

  const selectedCount = currentSession?.suggestions.filter((s) => s.selected).length || 0
  const canSave = selectedCount >= 3

  const SidebarHeader = ({ isDesktop = false }: { isDesktop?: boolean }) => (
    <div className="p-4 border-b">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-bold text-gray-900">
          {desktopSidebarOpen || !isDesktop ? "CCTalk 添削システム" : "CCTalk"}
        </h1>
        {isDesktop && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setDesktopSidebarOpen(!desktopSidebarOpen)}
            className="h-8 w-8 p-0"
          >
            <Menu className="w-4 h-4" />
          </Button>
        )}
      </div>
    </div>
  )

  const SidebarContent = ({ collapsed = false }: { collapsed?: boolean }) => (
    <div className={`h-full flex flex-col ${collapsed ? 'items-center w-16' : ''}`}>
      <div className={`p-4 border-b ${collapsed ? 'px-2' : ''}`}>
        {!collapsed && (
          <Button onClick={createNewSession} className="w-full" size="sm">
            <Plus className="w-4 h-4 mr-2" />
            新しいセッション
          </Button>
        )}
        {collapsed && (
          <Button onClick={createNewSession} size="icon" className="w-8 h-8">
            <Plus className="w-4 h-4" />
          </Button>
        )}
      </div>
      <ScrollArea className={`flex-1 ${collapsed ? 'px-1' : 'p-4'}`}>
        <div className="space-y-2">
          {sessions.map((session) => (
            <div
              key={session.id}
              className={`group p-3 rounded-lg border cursor-pointer transition-colors ${
                currentSessionId === session.id ? "bg-blue-50 border-blue-200" : "hover:bg-gray-50"
              } ${collapsed ? 'p-1' : ''}`}
              onClick={() => handleSessionSwitch(session.id)}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <h3 className={`font-medium text-sm truncate ${collapsed ? 'hidden' : ''}`}>{session.name}</h3>
                  <div className={`flex items-center gap-2 mt-1 ${collapsed ? 'justify-center' : ''}`}>
                    <Calendar className="w-3 h-3 text-gray-400" />
                    {!collapsed && (
                      <span className="text-xs text-gray-500">{session.createdAt.toLocaleDateString()}</span>
                    )}
                  </div>
                  <Badge variant="secondary" className={`mt-2 ${collapsed ? 'mx-auto block' : ''}`}>
                    保存済み: {session.correctionCount}件
                  </Badge>
                </div>
                {!collapsed && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation()
                      deleteSession(session.id)
                    }}
                    className="opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <Trash2 className="w-3 h-3" />
                  </Button>
                )}
              </div>
            </div>
          ))}

          {sessions.length === 0 && (
            <div className="text-center py-8 text-gray-500">
              <FileText className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">セッションがありません</p>
            </div>
          )}
        </div>
      </ScrollArea>
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
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    )
  }

  // 未認証の場合はログイン画面を表示し、保護されたエンドポイントへのアクセスを行わない
  if (!session) {
    return <LoginScreen />
  }

  return (
    <div className="h-screen flex flex-col bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Mobile Sidebar */}
      <Sheet open={sidebarOpen} onOpenChange={setSidebarOpen}>
        <SheetTrigger asChild>
          <Button variant="outline" size="sm" className="fixed top-4 left-4 z-50 lg:hidden bg-white shadow-md">
            <Menu className="w-4 h-4" />
          </Button>
        </SheetTrigger>
        <SheetContent side="left" className="w-80 p-0">
          <SheetHeader className="p-4 border-b">
            <SheetTitle>セッション管理</SheetTitle>
          </SheetHeader>
          <SidebarContent />
        </SheetContent>
      </Sheet>

      <div className="flex flex-1 min-h-0">
        {/* Desktop collapsed sidebar menu button */}
        {!desktopSidebarOpen && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => setDesktopSidebarOpen(true)}
            className="fixed top-4 left-4 z-50 hidden lg:block bg-white shadow-md"
          >
            <Menu className="w-4 h-4" />
          </Button>
        )}

        {/* Desktop Sidebar - Fixed */}
        {desktopSidebarOpen && (
          <div className="hidden lg:flex lg:flex-col w-80 h-full bg-white border-r shadow-sm flex-shrink-0">
            <SidebarHeader isDesktop={true} />
            <SidebarContent />
          </div>
        )}

        {/* Main Content - Scrollable */}
        <div className="flex-1 overflow-y-auto relative">
          {/* Global Logout Button - Top Right */}
          <Button
            variant="outline"
            size="sm"
            onClick={() => signOut()}
            className="fixed top-4 right-4 z-50 bg-white shadow-md"
            title="ログアウト"
          >
            <LogOut className="w-4 h-4" />
          </Button>
          <div className="p-4 lg:p-8">
            <div className="max-w-7xl mx-auto">
              {/* Header for mobile */}
              <div className="lg:hidden mb-6 pt-12">
                <h1 className="text-2xl font-bold text-gray-900">CCTalk 添削システム</h1>
              </div>

              {!currentSession ? (
                <div className="flex items-center justify-center min-h-[calc(100vh-8rem)]">
                  <Card className="max-w-md w-full mx-4">
                    <CardHeader className="text-center">
                      <FileText className="w-12 h-12 mx-auto mb-4 text-blue-600" />
                      <CardTitle>セッションを開始</CardTitle>
                      <CardDescription>新しいセッションを作成して添削を開始しましょう</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <Button onClick={createNewSession} className="w-full" size="lg">
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
                      <h2 className="text-xl font-bold text-gray-900">{currentSession.name}</h2>
                      <p className="text-sm text-gray-500">作成日: {currentSession.createdAt.toLocaleString()}</p>
                    </div>
                    {currentSession.savedData.length > 0 && (
                      <Badge variant="outline">保存済み: {currentSession.savedData.length}件</Badge>
                    )}
                  </div>

                  {/* Two Column Layout for Text Areas and Suggestions */}
                  <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                    {/* Left Column - Fixed Text Areas */}
                    <div className="space-y-6 xl:sticky xl:top-6 xl:h-fit">
                      {/* Original Text Input */}
                      <Card>
                        <CardHeader>
                          <CardTitle className="text-lg">原文テキスト</CardTitle>
                          <CardDescription>CCTalkから原文テキストをコピー&ペーストしてください</CardDescription>
                        </CardHeader>
                        <CardContent>
                          <Textarea
                            placeholder="原文テキストをここに貼り付けてください..."
                            value={currentSession.originalText}
                            onChange={(e) => updateCurrentSession({ originalText: e.target.value })}
                            className="min-h-[200px] text-base leading-relaxed"
                          />
                        </CardContent>
                      </Card>

                      {/* Target Text Input */}
                      <Card>
                        <CardHeader>
                          <CardTitle className="text-lg">添削対象テキスト</CardTitle>
                          <CardDescription>添削したいテキストをコピー&ペーストしてください</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                          <Textarea
                            placeholder="添削対象テキストをここに貼り付けてください..."
                            value={currentSession.targetText}
                            onChange={(e) => updateCurrentSession({ targetText: e.target.value })}
                            className="min-h-[250px] text-base leading-relaxed"
                          />
                          {/* Offline mode toggle */}
                          <div className="flex items-center justify-between p-3 bg-gray-50 border rounded-lg">
                            <div className="flex items-center gap-2">
                              <Checkbox
                                id="offline-mode"
                                checked={offlineMode}
                                onCheckedChange={(checked) => setOfflineMode(checked === true)}
                                disabled={webgpuSupported === false}
                              />
                              <Label htmlFor="offline-mode" className="text-sm cursor-pointer">
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
                            <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-sm text-yellow-800">
                              <p className="font-medium">オフラインモード利用不可</p>
                              <p className="text-xs mt-1">{webgpuUnsupportedReason}</p>
                              <p className="text-xs mt-1">クラウドAPIが利用できない場合、手動でカスタム修正を追加してください。</p>
                            </div>
                          )}
                          
                          {/* AI Diagnostics Panel - shows during any processing */}
                          {(webllmStatus.state === "loading" || 
                            webllmStatus.state === "generating" || 
                            webllmStatus.state === "checking_webgpu" ||
                            webllmStatus.state === "error") && (
                            <AIDiagnosticsPanel status={webllmStatus} />
                          )}
                          
                          <Button
                            onClick={handleGenerateClick}
                            disabled={!currentSession.targetText.trim() || (offlineMode && webgpuSupported === false)}
                            className="w-full"
                          >
                            {(() => {
                              const processingCount = jobQueue.filter(j => j.status === 'processing').length
                              const queuedCount = jobQueue.filter(j => j.status === 'queued').length
                              
                              return (
                                <>
                                  <Bot className="w-4 h-4 mr-2" />
                                  AI提案を生成
                                  {(processingCount > 0 || queuedCount > 0) && (
                                    <Badge variant="secondary" className="ml-2 text-xs">
                                      {processingCount > 0 && `処理中: ${processingCount}`}
                                      {processingCount > 0 && queuedCount > 0 && ' / '}
                                      {queuedCount > 0 && `待機: ${queuedCount}`}
                                    </Badge>
                                  )}
                                  {offlineMode && !isEngineReady() && (
                                    <span className="ml-1 text-xs">（初回DL）</span>
                                  )}
                                </>
                              )
                            })()}
                          </Button>
                        </CardContent>
                      </Card>
                    </div>

                    {/* Right Column - Suggestions and Actions */}
                    <div className="space-y-6">
                      {/* AI Suggestions */}
                      {currentSession.suggestions.length > 0 && (
                        <Card data-suggestions-card>
                          <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                              <Bot className="w-5 h-5 text-blue-600" />
                              AI修正提案
                              {confirmingJobId && (
                                <Badge variant="outline" className="ml-2 text-blue-600 border-blue-300">
                                  確認中
                                </Badge>
                              )}
                            </CardTitle>
                            <CardDescription>
                              以下の提案から3つ以上選択してください。修正内容とコメントは編集可能です。
                            </CardDescription>
                            <div className="flex items-center gap-2 flex-wrap">
                              <Badge variant={canSave ? "default" : "secondary"}>選択済み: {selectedCount}/5+</Badge>
                              {canSave && (
                                <Badge variant="outline" className="text-green-600">
                                  保存可能
                                </Badge>
                              )}
                            </div>
                          </CardHeader>
                          <CardContent className="space-y-4">
                            {currentSession.suggestions.map((suggestion) => (
                              <div key={suggestion.id} className="border rounded-lg p-4 space-y-3">
                                <div className="flex items-start gap-4">
                                  <div className="flex flex-col items-center gap-2">
                                    <Checkbox
                                      checked={suggestion.selected}
                                      onCheckedChange={() => toggleSuggestionSelection(suggestion.id)}
                                      className="h-5 w-5"
                                    />
                                    {suggestion.selected && suggestion.selectedOrder && (
                                      <Badge variant="outline" className="text-xs px-1 py-0">
                                        {suggestion.selectedOrder}
                                      </Badge>
                                    )}
                                  </div>
                                  <div className="flex-1 space-y-3">
                                    {suggestion.isCustom && (
                                      <Badge variant="outline" className="text-purple-600 border-purple-200">
                                        カスタム修正
                                      </Badge>
                                    )}
                                    <div className="grid grid-cols-1 gap-4">
                                      <div>
                                        <Label className="text-sm font-medium text-red-600">指摘箇所</Label>
                                        <p className="bg-red-50 p-3 rounded border text-sm mt-1 leading-relaxed">
                                          {suggestion.original}
                                        </p>
                                      </div>
                                    </div>
                                    <div className="bg-blue-50 p-3 rounded">
                                      <Label className="text-sm font-medium text-blue-600">修正コメント</Label>
                                      {suggestion.selected ? (
                                        <Textarea
                                          value={suggestion.userModifiedReason || suggestion.reason}
                                          onChange={(e) => updateSuggestionReason(suggestion.id, e.target.value)}
                                          className="text-sm min-h-[80px] mt-1 bg-white"
                                        />
                                      ) : (
                                        <p className="text-sm text-blue-800 mt-1 leading-relaxed">
                                          {suggestion.reason}
                                        </p>
                                      )}
                                    </div>
                                  </div>
                                </div>
                              </div>
                            ))}

                            {/* Custom Correction Form */}
                            {showCustomForm && (
                              <div className="border-2 border-dashed border-gray-300 rounded-lg p-4 space-y-4 bg-gray-50">
                                <div className="flex items-center gap-2">
                                  <Plus className="w-4 h-4 text-gray-600" />
                                  <Label className="text-sm font-medium text-gray-700">修正内容を追加</Label>
                                </div>
                                <div className="grid grid-cols-1 gap-4">
                                  <div>
                                    <Label htmlFor="custom-original" className="text-sm font-medium text-red-600">
                                      修正前のテキスト
                                    </Label>
                                    <Input
                                      id="custom-original"
                                      value={customCorrection.original}
                                      onChange={(e) =>
                                        setCustomCorrection((prev) => ({ ...prev, original: e.target.value }))
                                      }
                                      placeholder="修正前のテキストを入力"
                                      className="mt-1"
                                    />
                                  </div>
                                </div>
                                <div>
                                  <Label htmlFor="custom-reason" className="text-sm font-medium text-blue-600">
                                    修正コメント
                                  </Label>
                                  <Textarea
                                    id="custom-reason"
                                    value={customCorrection.reason}
                                    onChange={(e) =>
                                      setCustomCorrection((prev) => ({ ...prev, reason: e.target.value }))
                                    }
                                    placeholder="修正コメントを入力"
                                    className="min-h-[80px] mt-1"
                                  />
                                </div>
                                <Button onClick={addCustomCorrection} size="sm" className="w-full">
                                  <Plus className="w-4 h-4 mr-2" />
                                  修正内容を追加
                                </Button>
                              </div>
                            )}

                            {/* Overall Comment */}
                            {currentSession.overallComment && (
                              <div className="border rounded-lg p-4 bg-blue-50 border-blue-200">
                                <div className="flex items-center gap-2 mb-3">
                                  <MessageSquare className="w-4 h-4 text-blue-600" />
                                  <Label className="text-sm font-medium text-blue-700">全体総括コメント</Label>
                                </div>
                                <Textarea
                                  value={currentSession.overallComment}
                                  onChange={(e) => updateCurrentSession({ overallComment: e.target.value })}
                                  className="min-h-[100px] bg-white"
                                  placeholder="全体的な総括コメントを入力してください..."
                                />
                              </div>
                            )}

                            <Separator />

                            <Button onClick={saveCorrections} disabled={!canSave} className="w-full" size="lg">
                              <Copy className="w-4 h-4 mr-2" />
                              確定してコピー・保存 ({selectedCount}/3)
                            </Button>
                          </CardContent>
                        </Card>
                      )}

                      {/* Job Queue - Active Jobs */}
                      {jobQueue.length > 0 && (
                        <Card>
                          <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                              <Loader2 className="w-5 h-5 text-blue-600" />
                              ジョブキュー
                              <Badge variant="secondary" className="ml-2">
                                {jobQueue.filter(j => j.status === 'processing').length} 処理中 / {jobQueue.filter(j => j.status === 'queued').length} 待機
                              </Badge>
                            </CardTitle>
                            <CardDescription>
                              {offlineMode 
                                ? "WebLLMモード: 逐次処理（1件ずつ）" 
                                : `APIモード: 並列処理（最大${MAX_CONCURRENT_API_JOBS}件同時）`}
                            </CardDescription>
                          </CardHeader>
                          <CardContent>
                            <div className="space-y-3">
                              {jobQueue.map((job) => {
                                const isClickable = job.status === 'completed' && job.suggestions
                                return (
                                  <div 
                                    key={job.id} 
                                    className={`border rounded-lg p-4 space-y-2 transition-colors ${
                                      job.status === 'processing' 
                                        ? 'bg-blue-50 border-blue-200' 
                                        : job.status === 'completed'
                                        ? 'bg-green-50 border-green-200'
                                        : job.status === 'failed'
                                        ? 'bg-red-50 border-red-200'
                                        : 'bg-gray-50 border-gray-200'
                                    } ${isClickable ? 'cursor-pointer hover:bg-green-100 hover:border-green-300' : ''}`}
                                    onClick={isClickable ? () => confirmJob(job) : undefined}
                                    onKeyDown={isClickable ? (e) => {
                                      if (e.key === 'Enter' || e.key === ' ') {
                                        e.preventDefault()
                                        confirmJob(job)
                                      }
                                    } : undefined}
                                    role={isClickable ? 'button' : undefined}
                                    tabIndex={isClickable ? 0 : undefined}
                                    aria-label={isClickable ? `確認: ${job.targetText.slice(0, 30)}...` : undefined}
                                  >
                                    <div className="flex justify-between items-start">
                                      <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2">
                                          {job.status === 'processing' && <Loader2 className="w-4 h-4 animate-spin text-blue-600" />}
                                          {job.status === 'completed' && <CheckCircle className="w-4 h-4 text-green-600" />}
                                          {job.status === 'failed' && <span className="text-red-600">✕</span>}
                                          {job.status === 'queued' && <span className="text-gray-400">○</span>}
                                          <Badge variant={
                                            job.status === 'processing' ? 'default' :
                                            job.status === 'completed' ? 'outline' :
                                            job.status === 'failed' ? 'destructive' : 'secondary'
                                          }>
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
                                        <p className="text-xs text-gray-500 mt-1 truncate">
                                          {job.targetText.slice(0, 50)}{job.targetText.length > 50 ? '...' : ''}
                                        </p>
                                        <p className="text-xs text-gray-400">
                                          {job.queuedAt.toLocaleTimeString()}
                                          {job.completedAt && ` → ${job.completedAt.toLocaleTimeString()}`}
                                        </p>
                                        {job.error && (
                                          <p className="text-xs text-red-600 mt-1">{job.error}</p>
                                        )}
                                      </div>
                                      {isClickable && (
                                        <div className="flex items-center text-sm text-green-700 font-medium">
                                          <CheckCircle className="w-4 h-4 mr-1" />
                                          確認
                                        </div>
                                      )}
                                    </div>
                                  </div>
                                )
                              })}
                            </div>
                          </CardContent>
                        </Card>
                      )}

                      {/* Saved Data History */}
                      {currentSession.savedData.length > 0 && (
                        <Card>
                          <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                              <CheckCircle className="w-5 h-5 text-green-600" />
                              実行履歴
                            </CardTitle>
                            <CardDescription>このセッションで保存された添削データ</CardDescription>
                          </CardHeader>
                          <CardContent>
                            <div className="space-y-3">
                              {currentSession.savedData.map((data, index) => (
                                <div 
                                  key={index} 
                                  className={`border rounded-lg p-4 space-y-3 ${
                                    data.confirmed 
                                      ? 'bg-green-50 border-green-200' 
                                      : 'bg-gray-50 border-gray-200'
                                  }`}
                                >
                                  <div className="flex justify-between items-start">
                                    <div>
                                      <div className="flex items-center gap-2">
                                        <h4 className="font-medium text-sm">添削データ #{index + 1}</h4>
                                        {!data.confirmed && (
                                          <Badge variant="outline" className="text-gray-600 border-gray-300 text-xs">
                                            未確認
                                          </Badge>
                                        )}
                                      </div>
                                      <p className="text-xs text-gray-500">{data.timestamp.toLocaleString()}</p>
                                    </div>
                                    <div className="flex gap-2">
                                      <Button 
                                        variant={data.confirmed ? "ghost" : "outline"} 
                                        size="sm" 
                                        onClick={() => {
                                          restoreFromHistory(data)
                                          setConfirmingHistoryIndex(index)
                                        }}
                                      >
                                        <CheckCircle className={`w-3 h-3 mr-1 ${data.confirmed ? 'text-green-600' : ''}`} />
                                        {data.confirmed ? '確認済み' : '確認'}
                                      </Button>
                                      <Button
                                        variant="outline"
                                        size="sm"
                                        onClick={() => console.log("削除機能未実装")}
                                      >
                                        <Trash2 className="w-3 h-3 mr-1" />
                                        削除
                                      </Button>
                                    </div>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </CardContent>
                        </Card>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
