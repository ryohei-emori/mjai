"use client"

import { useEffect, useCallback, useRef } from "react"
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
  RotateCcw,
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
  WebGPUUnsupportedError,
  ModelLoadError,
  InferenceError,
  TimeoutError,
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
  result?: SavedData
  error?: string
  queuedAt: Date
  completedAt?: Date
}

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

const FRONTEND_MODE = process.env.NEXT_PUBLIC_FRONTEND_MODE || "real"

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
      
      {/* Timeout info */}
      {diagnostics?.timeoutPhase && (
        <div className="mt-2 p-2 bg-red-100 rounded text-xs text-red-800">
          <strong>タイムアウト:</strong> {PHASE_LABELS[diagnostics.timeoutPhase]} フェーズでタイムアウトしました
        </div>
      )}
      
      {/* Error message */}
      {status.state === "error" && (
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
  const [isProcessing, setIsProcessing] = useState(false)
  const [customCorrection, setCustomCorrection] = useState({ original: "", reason: "" })
  const [showCustomForm, setShowCustomForm] = useState(false)
  const [selectionCounter, setSelectionCounter] = useState(0)
  const [webllmStatus, setWebllmStatus] = useState<EngineStatus>({ state: "idle" })
  const [webgpuSupported, setWebgpuSupported] = useState<boolean | null>(null)
  const [webgpuUnsupportedReason, setWebgpuUnsupportedReason] = useState<string | null>(null)
  const [offlineMode, setOfflineMode] = useState(false)
  const [lastSuggestionSource, setLastSuggestionSource] = useState<"api" | "webllm" | null>(null)
  const [jobQueue, setJobQueue] = useState<QueuedJob[]>([])
  const [confirmingHistoryIndex, setConfirmingHistoryIndex] = useState<number | null>(null)
  const { toast } = useToast()

  // Check WebGPU support on mount
  useEffect(() => {
    const check = checkWebGPUSupport()
    setWebgpuSupported(check.supported)
    if (!check.supported) {
      setWebgpuUnsupportedReason(check.reason || "WebGPU is not supported")
    }
  }, [])

  // Periodic timer updates during processing
  // This fixes the "0ms" display bug by polling the tracker for fresh timing data
  useEffect(() => {
    if (!isProcessing) return
    
    // Only update when in active processing states
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
  }, [isProcessing, webllmStatus.state])

  // ジョブをキューに追加する関数
  const addToQueue = useCallback((targetText: string) => {
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
    
    const queuedCount = currentQueueSize + 1
    toast({
      title: "キューに追加",
      description: `ジョブをキューに追加しました（待機中: ${queuedCount}件）`,
    })
    
    return true
  }, [jobQueue, toast])

  // キュー消化ループ - queuedジョブをprocessingに移行して処理
  useEffect(() => {
    const processNextJob = async () => {
      // 処理中の場合は何もしない
      if (isProcessing) return
      
      // 処理中のジョブがあれば何もしない
      const processingJob = jobQueue.find(j => j.status === 'processing')
      if (processingJob) return

      // 次のqueuedジョブを取得
      const nextJob = jobQueue.find(j => j.status === 'queued')
      if (!nextJob || !currentSession) return

      // ジョブをprocessingに更新
      setJobQueue(prev => prev.map(j => 
        j.id === nextJob.id ? { ...j, status: 'processing' as const } : j
      ))

      // セッションのターゲットテキストを更新
      updateCurrentSession({ targetText: nextJob.targetText })

      // 処理中の通知
      const queuedCount = jobQueue.filter(j => j.status === 'queued').length - 1
      toast({
        title: "処理中",
        description: queuedCount > 0 
          ? `AI添削を実行中...（残り: ${queuedCount}件）`
          : "AI添削を実行中...",
      })
    }

    processNextJob()
  }, [jobQueue, currentSession, isProcessing, toast])

  // ジョブ処理完了時のハンドラー
  const completeCurrentJob = useCallback((success: boolean, error?: string) => {
    const processingJob = jobQueue.find(j => j.status === 'processing')
    if (!processingJob) return

    setJobQueue(prev => prev.map(j => 
      j.id === processingJob.id 
        ? { 
            ...j, 
            status: success ? 'completed' as const : 'failed' as const,
            completedAt: new Date(),
            error: error,
          } 
        : j
    ))

    if (success) {
      toast({
        title: "完了",
        description: "AI添削が完了しました",
      })
    }
  }, [jobQueue, toast])

  // ボタンクリックハンドラー - 処理中ならキューに追加、そうでなければ直接実行
  const handleGenerateClick = useCallback(() => {
    if (!currentSession?.targetText.trim()) return

    if (isProcessing) {
      // 処理中の場合はキューに追加
      addToQueue(currentSession.targetText)
      // テキストエリアをクリアして次の入力を待つ
      updateCurrentSession({ targetText: "" })
    }
    // 処理中でない場合は、ボタンのonClickでgenerateAISuggestionsが呼ばれる
  }, [currentSession, isProcessing, addToQueue])

  const mockSuggestions: CorrectionSuggestion[] = [
    {
      id: "1",
      original: "我并不想回复",
      reason:
        "ようがない并非不想的含义，这里可以再看一下这个文法的含义\nようがない：〜できない / 〜したくても手段がない\n不可能であることを強調して言う時に使う。",
      selected: false,
    },
    {
      id: "2",
      original: "どんな担任にあったか",
      reason: "担任指的是学校的老师哦\n担任：学校で，教師があるクラス・教科などを受け持つこと。また，その教師。",
      selected: false,
    },
    {
      id: "3",
      original: "有个孩子霸凌年纪比较小的孩子",
      reason: "这里最好把問題行為译出来哦",
      selected: false,
    },
    {
      id: "4",
      original: "",
      reason: "",
      selected: false,
    },
    {
      id: "5",
      original: "",
      reason: "",
      selected: false,
    },
  ]

  const mockOverallComment =
    "译文整体的流畅性和对原意翻译处理和展现比较不错，可以再看一下以上几点，注意积累一下ようがない和担任的含义，加油～"

  const currentSession = sessions.find((s) => s.id === currentSessionId)

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

  // セッション詳細をオンデマンドで取得
  const loadSessionDetails = async (sessionId: string) => {
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
  }

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

  // セッション更新をAPIに実行
  const updateCurrentSession = (updates: Partial<Session>) => {
    if (!currentSessionId) return
    setSessions((prev) =>
      prev.map((session) => (session.id === currentSessionId ? { ...session, ...updates } : session)),
    )
  }

  // AI提案生成: API優先、WebLLMフォールバック（既存の選択状態を保持）
  const generateAISuggestions = async () => {
    if (!currentSession?.targetText.trim()) return

    setIsProcessing(true)
    setLastSuggestionSource(null)

    // 既存の選択状態とカスタム修正を保存
    const existingSelections = new Map()
    const existingCustomCorrections: CorrectionSuggestion[] = []

    if (currentSession.suggestions.length > 0) {
      currentSession.suggestions.forEach((suggestion) => {
        if (suggestion.isCustom) {
          existingCustomCorrections.push(suggestion)
        } else if (suggestion.selected || suggestion.userModifiedReason) {
          existingSelections.set(suggestion.original, {
            selected: suggestion.selected,
            selectedOrder: suggestion.selectedOrder,
            userModifiedReason: suggestion.userModifiedReason,
          })
        }
      })
    }

    if (FRONTEND_MODE === "mock") {
      // 既存の選択状態を復元
      const restoredSuggestions = mockSuggestions.map((s) => {
        const existing = existingSelections.get(s.original)
        return existing ? { ...s, ...existing } : { ...s, selected: false, selectedOrder: undefined }
      })

      // カスタム修正を追加
      const allSuggestions = [...restoredSuggestions, ...existingCustomCorrections]

      updateCurrentSession({
        suggestions: allSuggestions,
        overallComment: mockOverallComment,
      })
      setShowCustomForm(true)

      // 選択カウンターを復元
      const selectedCount = allSuggestions.filter((s) => s.selected).length
      setSelectionCounter(selectedCount)

      setIsProcessing(false)
      return
    }

    // Helper function to apply suggestions
    const applySuggestions = (data: { suggestions: Array<{ id: string; original: string; reason: string }>; overallComment: string }) => {
      const restoredSuggestions = data.suggestions.map((s) => {
        const existing = existingSelections.get(s.original)
        return existing
          ? { ...s, ...existing, selected: existing.selected || false }
          : { ...s, selected: false, selectedOrder: undefined }
      })

      const allSuggestions = [...restoredSuggestions, ...existingCustomCorrections]

      updateCurrentSession({
        suggestions: allSuggestions,
        overallComment: data.overallComment,
      })
      setShowCustomForm(true)

      const selectedCount = allSuggestions.filter((s) => s.selected).length
      setSelectionCounter(selectedCount)
    }

    // オフラインモードの場合はWebLLMを直接使用
    if (offlineMode) {
      if (!webgpuSupported) {
        toast({
          title: "WebGPU非対応",
          description: webgpuUnsupportedReason || "このブラウザではオフラインモードを利用できません",
          variant: "destructive",
        })
        setIsProcessing(false)
        return
      }

      try {
        const data = await generateWebLLMSuggestions(
          {
            originalText: currentSession.originalText,
            targetText: currentSession.targetText,
            instructionPrompt: "CCTalkからの添削指示",
          },
          (status) => setWebllmStatus(status)
        )
        applySuggestions(data)
        setLastSuggestionSource("webllm")
      } catch (error) {
        let errorMessage = "AI提案の生成に失敗しました"
        if (error instanceof WebGPUUnsupportedError) {
          errorMessage = error.message
          setWebgpuSupported(false)
          setWebgpuUnsupportedReason(error.message)
        } else if (error instanceof TimeoutError) {
          errorMessage = error.message
        } else if (error instanceof ModelLoadError) {
          errorMessage = `モデルの読み込みに失敗しました: ${error.message}`
        } else if (error instanceof InferenceError) {
          errorMessage = `推論に失敗しました: ${error.message}`
        }
        toast({ title: "エラー", description: errorMessage, variant: "destructive" })
        setWebllmStatus({ state: "idle" })
      } finally {
        setIsProcessing(false)
      }
      return
    }

    // API優先モード: まずAPIを試し、失敗したらWebLLMにフォールバック
    try {
      setWebllmStatus({ state: "generating", progress: 0, text: "クラウドAPI接続中..." })
      const data = await suggestionsAPI.generate(currentSession.originalText, currentSession.targetText)
      applySuggestions(data)
      setLastSuggestionSource("api")
      setWebllmStatus({ state: "idle" })
    } catch (apiError) {
      console.warn("[suggestions] API failed, falling back to WebLLM:", apiError)
      
      // WebGPUがサポートされていない場合はエラーを表示して終了
      if (!webgpuSupported) {
        toast({
          title: "API接続エラー",
          description: "クラウドAPIに接続できませんでした。WebGPUも非対応のため、AI提案機能を利用できません。",
          variant: "destructive",
        })
        setWebllmStatus({ state: "idle" })
        setIsProcessing(false)
        return
      }

      // WebLLMにフォールバック
      toast({
        title: "オフラインモードに切り替え",
        description: "クラウドAPIに接続できませんでした。ローカルAIモデルを使用します。",
      })

      try {
        const data = await generateWebLLMSuggestions(
          {
            originalText: currentSession.originalText,
            targetText: currentSession.targetText,
            instructionPrompt: "CCTalkからの添削指示",
          },
          (status) => setWebllmStatus(status)
        )
        applySuggestions(data)
        setLastSuggestionSource("webllm")
      } catch (webllmError) {
        let errorMessage = "AI提案の生成に失敗しました"
        if (webllmError instanceof WebGPUUnsupportedError) {
          errorMessage = webllmError.message
          setWebgpuSupported(false)
          setWebgpuUnsupportedReason(webllmError.message)
        } else if (webllmError instanceof TimeoutError) {
          errorMessage = webllmError.message
        } else if (webllmError instanceof ModelLoadError) {
          errorMessage = `モデルの読み込みに失敗しました: ${(webllmError as Error).message}`
        } else if (webllmError instanceof InferenceError) {
          errorMessage = `推論に失敗しました: ${(webllmError as Error).message}`
        }
        toast({ title: "エラー", description: errorMessage, variant: "destructive" })
        setWebllmStatus({ state: "idle" })
      }
    } finally {
      setIsProcessing(false)
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
      const savedData: SavedData = {
        originalText: currentSession.originalText,
        instructionPrompt: "CCTalkからの添削指示",
        targetText: currentSession.targetText,
        aiSuggestions: currentSession.suggestions,
        selectedCorrections: selectedSuggestions,
        overallComment: currentSession.overallComment,
        combinedComment,
        timestamp: new Date(),
      }

      updateCurrentSession({
        savedData: [...currentSession.savedData, savedData],
        targetText: "",
        suggestions: [],
        overallComment: "",
      })

      setShowCustomForm(false)
      setCustomCorrection({ original: "", reason: "" })
      setSelectionCounter(0)

      toast({
        title: "保存完了",
        description: "修正内容が保存され、クリップボードにコピーされました",
      })
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
      title: "履歴を復元しました",
      description: "選択した履歴データが現在のセッションに復元されました",
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
              onClick={() => {
                setCurrentSessionId(session.id)
                setSidebarOpen(false)
                loadSessionDetails(session.id)
              }}
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
                            onClick={() => {
                              if (isProcessing) {
                                handleGenerateClick()
                              } else {
                                generateAISuggestions()
                              }
                            }}
                            disabled={!currentSession.targetText.trim() || (offlineMode && webgpuSupported === false)}
                            className="w-full"
                          >
                            {isProcessing ? (
                              <>
                                <Plus className="w-4 h-4 mr-2" />
                                キューに追加
                                {jobQueue.filter(j => j.status === 'queued').length > 0 && (
                                  <Badge variant="secondary" className="ml-2 text-xs">
                                    待機: {jobQueue.filter(j => j.status === 'queued').length}
                                  </Badge>
                                )}
                              </>
                            ) : offlineMode ? (
                              isEngineReady() ? (
                                <>
                                  <Bot className="w-4 h-4 mr-2" />
                                  AI提案を生成（オフライン）
                                </>
                              ) : (
                                <>
                                  <Bot className="w-4 h-4 mr-2" />
                                  AI提案を生成（初回は{WEBLLM_MODEL_DISPLAY_NAME}をDL）
                                </>
                              )
                            ) : (
                              <>
                                <Bot className="w-4 h-4 mr-2" />
                                AI提案を生成
                              </>
                            )}
                          </Button>
                        </CardContent>
                      </Card>
                    </div>

                    {/* Right Column - Suggestions and Actions */}
                    <div className="space-y-6">
                      {/* AI Suggestions */}
                      {currentSession.suggestions.length > 0 && (
                        <Card>
                          <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                              <Bot className="w-5 h-5 text-blue-600" />
                              AI修正提案
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
                              <div className="border rounded-lg p-4 bg-yellow-50">
                                <div className="flex items-center gap-2 mb-3">
                                  <MessageSquare className="w-4 h-4 text-yellow-600" />
                                  <Label className="text-sm font-medium text-yellow-700">全体総括コメント</Label>
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

                      {/* Saved Data History */}
                      {currentSession.savedData.length > 0 && (
                        <Card>
                          <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                              <CheckCircle className="w-5 h-5 text-green-600" />
                              保存履歴
                            </CardTitle>
                            <CardDescription>このセッションで保存された添削データ</CardDescription>
                          </CardHeader>
                          <CardContent>
                            <div className="space-y-3">
                              {currentSession.savedData.map((data, index) => (
                                <div key={index} className="border rounded-lg p-4 space-y-3">
                                  <div className="flex justify-between items-start">
                                    <div>
                                      <h4 className="font-medium text-sm">添削データ #{index + 1}</h4>
                                      <p className="text-xs text-gray-500">{data.timestamp.toLocaleString()}</p>
                                    </div>
                                    <div className="flex gap-2">
                                      <Button variant="outline" size="sm" onClick={() => restoreFromHistory(data)}>
                                        <RotateCcw className="w-3 h-3 mr-1" />
                                        復元
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
