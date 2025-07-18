"use client"

import { useEffect } from "react"
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
} from "lucide-react"
import { useToast } from "@/hooks/use-toast"
import { sessionAPI, historyAPI, proposalAPI, suggestionsAPI } from "./api"

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
}

type Session = {
  id: string
  name: string
  createdAt: Date
  originalText: string
  targetText: string
  suggestions: CorrectionSuggestion[]
  overallComment: string
  savedData: SavedData[]
}

const FRONTEND_MODE = process.env.NEXT_PUBLIC_FRONTEND_MODE || "real";

export default function TextCorrectionApp() {
  const [sessions, setSessions] = useState<Session[]>([])
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [customCorrection, setCustomCorrection] = useState({ original: "", reason: "" })
  const [showCustomForm, setShowCustomForm] = useState(false)
  const [selectionCounter, setSelectionCounter] = useState(0)
  const { toast } = useToast()

  const mockSuggestions: CorrectionSuggestion[] = [
    {
      id: "1",
      original: "我并不想回复",
      reason: "ようがない并非不想的含义，这里可以再看一下这个文法的含义\nようがない：〜できない / 〜したくても手段がない\n不可能であることを強調して言う時に使う。",
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
  const loadSessions = async () => {
    try {
      console.log('Loading sessions...');
      const sessionsData = await sessionAPI.getSessions();
      console.log('Sessions data received:', sessionsData);
      
      // APIから取得したデータをフロントエンドのSession型に変換
      const convertedSessions: Session[] = [];
      
      for (const s of sessionsData) {
        console.log('Processing session:', s.sessionId);
        // 各セッションの履歴を取得
        const historiesData = await historyAPI.getHistories(s.sessionId);
        console.log('Histories for session', s.sessionId, ':', historiesData);
        const savedData: SavedData[] = [];
        
        for (const history of historiesData) {
          console.log('Processing history:', history.historyId);
          // 各履歴の提案を取得
          const proposalsData = await proposalAPI.getProposals(history.historyId);
          console.log('Proposals for history', history.historyId, ':', proposalsData);
          
          // 提案データをCorrectionSuggestion形式に変換
          const aiSuggestions: CorrectionSuggestion[] = proposalsData.map((proposal: any) => ({
            id: proposal.proposalId,
            original: proposal.originalAfterText,
            reason: proposal.originalReason || "",
            selected: proposal.isSelected === 1,
            selectedOrder: proposal.selectedOrder || undefined,
            userModifiedReason: proposal.isModified === 1 ? proposal.modifiedReason : undefined,
            isCustom: proposal.isCustom === 1
          }));
          
          // 選択された提案のみを抽出
          const selectedCorrections = aiSuggestions.filter(s => s.selected);
          
          savedData.push({
            originalText: history.originalText,
            instructionPrompt: history.instructionPrompt || "",
            targetText: history.targetText,
            aiSuggestions,
            selectedCorrections,
            overallComment: history.combinedComment || "",
            combinedComment: history.combinedComment || "",
            timestamp: new Date(history.timestamp)
          });
        }
        
        convertedSessions.push({
          id: s.sessionId,
          name: s.name || 'セッション',
          createdAt: new Date(s.createdAt),
          originalText: '',
          targetText: '',
          suggestions: [],
          overallComment: '',
          savedData
        });
      }
      
      console.log('Converted sessions:', convertedSessions);
      setSessions(convertedSessions);
    } catch (error) {
      console.error('Failed to load sessions:', error);
      toast({
        title: "エラー",
        description: "セッションの読み込みに失敗しました",
        variant: "destructive",
      });
    }
  };

  // セッション作成をAPIに保存
  const createNewSession = async () => {
    try {
      const newSessionData = await sessionAPI.createSession(`セッション ${sessions.length + 1}`);
      const newSession: Session = {
        id: newSessionData.sessionId,
        name: newSessionData.name,
        createdAt: new Date(newSessionData.createdAt),
        originalText: "",
        targetText: "",
        suggestions: [],
        overallComment: "",
        savedData: [],
      };
      setSessions((prev) => [newSession, ...prev]);
      setCurrentSessionId(newSession.id);
      setSidebarOpen(false);
      setSelectionCounter(0);
    } catch (error) {
      console.error('Failed to create session:', error);
      toast({
        title: "エラー",
        description: "セッションの作成に失敗しました",
        variant: "destructive",
      });
    }
  };

  // セッション削除をAPIに実行
  const deleteSession = async (sessionId: string) => {
    try {
      await sessionAPI.deleteSession(sessionId);
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      if (currentSessionId === sessionId) {
        const remainingSessions = sessions.filter((s) => s.id !== sessionId);
        setCurrentSessionId(remainingSessions.length > 0 ? remainingSessions[0].id : null);
      }
    } catch (error) {
      console.error('Failed to delete session:', error);
      toast({
        title: "エラー",
        description: "セッションの削除に失敗しました",
        variant: "destructive",
      });
    }
  };

  // セッション更新をAPIに実行
  const updateCurrentSession = (updates: Partial<Session>) => {
    if (!currentSessionId) return;
    setSessions((prev) =>
      prev.map((session) => (session.id === currentSessionId ? { ...session, ...updates } : session)),
    );
  };

  // AI提案生成をAPIから取得
  const generateAISuggestions = async () => {
    if (!currentSession?.targetText.trim()) return;

    setIsProcessing(true);

    if (FRONTEND_MODE === "mock") {
      updateCurrentSession({
        suggestions: mockSuggestions.map((s) => ({ ...s, selected: false, selectedOrder: undefined })),
        overallComment: mockOverallComment,
      });
      setShowCustomForm(true);
      setSelectionCounter(0);
      setIsProcessing(false);
      return;
    }

    try {
      const data = await suggestionsAPI.generateSuggestions({
        originalText: currentSession.originalText,
        targetText: currentSession.targetText,
        instructionPrompt: "CCTalkからの添削指示",
        sessionId: currentSession.id,
        engine: "gemini"
      });

      updateCurrentSession({
        suggestions: data.suggestions.map((s: any) => ({ ...s, selected: false, selectedOrder: undefined })),
        overallComment: data.overallComment,
      });
      setShowCustomForm(true);
      setSelectionCounter(0);
    } catch (e) {
      toast({
        title: "APIエラー",
        description: "AI提案の取得に失敗しました",
        variant: "destructive",
      });
    } finally {
      setIsProcessing(false);
    }
  };

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
    } catch (err) {
      toast({
        title: "コピー失敗",
        description: "クリップボードへのコピーに失敗しました",
        variant: "destructive",
      })
    }
  }

  // 履歴をAPIに保存
  const saveCorrections = async () => {
    if (!currentSession) return;

    const selectedSuggestions = currentSession.suggestions
      .filter((s) => s.selected)
      .sort((a, b) => (a.selectedOrder || 0) - (b.selectedOrder || 0));

    if (selectedSuggestions.length < 3) {
      toast({
        title: "選択不足",
        description: "3つ以上の修正内容を選択してください",
        variant: "destructive",
      });
      return;
    }

    try {
      // 履歴データを作成
      const historyData = {
        sessionId: currentSession.id,
        originalText: currentSession.originalText,
        targetText: currentSession.targetText,
        instructionPrompt: "CCTalkからの添削指示",
        combinedComment: currentSession.overallComment,
        selectedProposalIds: JSON.stringify(selectedSuggestions.map(s => s.id)),
        customProposals: JSON.stringify(selectedSuggestions.filter(s => s.isCustom))
      };

      // 履歴をAPIに保存
      const savedHistory = await historyAPI.createHistory(historyData);

      // すべての提案をAPIに保存（選択されたものも選択されていないものも）
      for (const suggestion of currentSession.suggestions) {
        const proposalData = {
          historyId: savedHistory.historyId,
          type: (suggestion.isCustom ? 'Custom' : 'AI') as 'AI' | 'Custom',
          originalAfterText: suggestion.original,
          originalReason: suggestion.reason,
          modifiedAfterText: suggestion.userModifiedReason ? suggestion.original : suggestion.original,
          modifiedReason: suggestion.userModifiedReason || suggestion.reason,
          isSelected: suggestion.selected ? 1 : 0,
          isModified: suggestion.userModifiedReason ? 1 : 0,
          isCustom: suggestion.isCustom ? 1 : 0,
          selectedOrder: suggestion.selected ? suggestion.selectedOrder : undefined
        };
        await proposalAPI.createProposal(proposalData);
      }

      // クリップボードにコピー
      const numberedCorrections = selectedSuggestions
        .map((suggestion, index) => {
          const reasonText = suggestion.userModifiedReason || suggestion.reason;
          return `${index + 1}.${suggestion.original}\n${reasonText}`;
        })
        .join("\n\n");

      const combinedComment = `${numberedCorrections}\n\n${currentSession.overallComment}`;
      await copyToClipboard(combinedComment);

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
      };

      updateCurrentSession({
        savedData: [...currentSession.savedData, savedData],
        targetText: "",
        suggestions: [],
        overallComment: "",
      });

      setShowCustomForm(false);
      setCustomCorrection({ original: "", reason: "" });
      setSelectionCounter(0);

      toast({
        title: "保存完了",
        description: "修正内容が保存され、クリップボードにコピーされました",
      });
    } catch (error) {
      console.error('Failed to save corrections:', error);
      toast({
        title: "エラー",
        description: "修正内容の保存に失敗しました",
        variant: "destructive",
      });
    }
  };

  // 履歴をAPIから復元
  const restoreFromHistory = (savedData: SavedData) => {
    if (!currentSession) return;

    updateCurrentSession({
      originalText: savedData.originalText,
      targetText: savedData.targetText,
      suggestions: savedData.aiSuggestions.map((s) => ({ 
        ...s, 
        selected: s.selected || false, 
        selectedOrder: s.selectedOrder 
      })),
      overallComment: savedData.overallComment,
    });

    // 選択カウンターを復元
    const selectedCount = savedData.aiSuggestions.filter(s => s.selected).length;
    setSelectionCounter(selectedCount);

    setShowCustomForm(true);

    toast({
      title: "履歴を復元しました",
      description: "選択した履歴データが現在のセッションに復元されました",
    });
  };

  const selectedCount = currentSession?.suggestions.filter((s) => s.selected).length || 0
  const canSave = selectedCount >= 3

  const SidebarContent = () => (
    <div className="h-full flex flex-col">
      <div className="p-4 border-b">
        <Button onClick={createNewSession} className="w-full" size="sm">
          <Plus className="w-4 h-4 mr-2" />
          新しいセッション
        </Button>
      </div>

      <ScrollArea className="flex-1 p-4">
        <div className="space-y-2">
          {sessions.map((session) => (
            <div
              key={session.id}
              className={`group p-3 rounded-lg border cursor-pointer transition-colors ${
                currentSessionId === session.id ? "bg-blue-50 border-blue-200" : "hover:bg-gray-50"
              }`}
              onClick={() => {
                setCurrentSessionId(session.id)
                setSidebarOpen(false)
              }}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <h3 className="font-medium text-sm truncate">{session.name}</h3>
                  <div className="flex items-center gap-2 mt-1">
                    <Calendar className="w-3 h-3 text-gray-400" />
                    <span className="text-xs text-gray-500">{session.createdAt.toLocaleDateString()}</span>
                  </div>
                  {session.savedData.length > 0 && (
                    <Badge variant="secondary" className="mt-2 text-xs">
                      保存済み: {session.savedData.length}件
                    </Badge>
                  )}
                </div>
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

  // 初期化時にセッションを読み込み
  useEffect(() => {
    loadSessions();
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Mobile Sidebar */}
      <Sheet open={sidebarOpen} onOpenChange={setSidebarOpen}>
        <SheetTrigger asChild>
          <Button variant="outline" size="sm" className="fixed top-4 left-4 z-50 lg:hidden bg-transparent">
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

      <div className="flex h-screen">
        {/* Desktop Sidebar */}
        <div className="hidden lg:block w-80 bg-white border-r shadow-sm">
          <div className="p-4 border-b">
            <h1 className="text-lg font-bold text-gray-900">CCTalk 添削システム</h1>
          </div>
          <SidebarContent />
        </div>

        {/* Main Content */}
        <div className="flex-1 overflow-auto">
          <div className="p-4 lg:p-8">
            <div className="max-w-4xl mx-auto">
              {/* Header for mobile */}
              <div className="lg:hidden mb-6 pt-12">
                <h1 className="text-2xl font-bold text-gray-900">CCTalk 添削システム</h1>
              </div>

              {!currentSession ? (
                <Card className="max-w-md mx-auto">
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
                        className="min-h-[120px]"
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
                        className="min-h-[120px]"
                      />
                      <Button
                        onClick={generateAISuggestions}
                        disabled={!currentSession.targetText.trim() || isProcessing}
                        className="w-full"
                      >
                        {isProcessing ? (
                          <>
                            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                            AI分析中...
                          </>
                        ) : (
                          <>
                            <Bot className="w-4 h-4 mr-2" />
                            AI提案を生成
                          </>
                        )}
                      </Button>
                    </CardContent>
                  </Card>

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
                                      className="text-sm min-h-[60px] mt-1 bg-white"
                                    />
                                  ) : (
                                    <p className="text-sm text-blue-800 mt-1 leading-relaxed">{suggestion.reason}</p>
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
                                onChange={(e) => setCustomCorrection((prev) => ({ ...prev, reason: e.target.value }))}
                                placeholder="修正コメントを入力"
                                className="min-h-[60px] mt-1"
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
                              className="min-h-[80px] bg-white"
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
                                    onClick={() => copyToClipboard(data.combinedComment)}
                                  >
                                    <Copy className="w-3 h-3 mr-1" />
                                    再コピー
                                  </Button>
                                </div>
                              </div>
                              <div className="text-sm text-gray-600 space-y-1">
                                <p>選択された修正: {data.selectedCorrections.length}件</p>
                                <p className="text-xs text-gray-500 truncate">
                                  添削対象: {data.targetText.substring(0, 50)}...
                                </p>
                              </div>
                            </div>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
