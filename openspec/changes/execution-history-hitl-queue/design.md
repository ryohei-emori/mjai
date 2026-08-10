## Context

現在の`page.tsx`は同期的なジョブ処理を行っており、`isProcessing`フラグで入力をブロックしている。`useToast`フックによるトースト通知は既に存在する。logoutボタンは`fixed top-4 right-4`に配置済み。

**重要**: クラウドAPI（`POST /api/suggestions` via Groq/Cloudflare）は本質的に並列リクエストをサポートしている。WebLLMのみが単一GPU/モデル制約により逐次処理を必要とする。

詳細はproposal.mdを参照。

## Goals / Non-Goals

**Goals:**
- クライアント側並列ジョブキュー実装（バックエンド変更不要）
- **APIモード**: 同時に複数リクエストを発行し、並列処理（上限: 3件）
- **WebLLMモード**: 逐次処理を維持（GPU/モデルリソース制約）
- 既存UIパターン（shadcn/ui、Tailwind）の活用
- 最小限の状態管理変更でキュー機能を追加

**Non-Goals:**
- バックエンドキュー/ワーカーシステムの実装
- WebSocket/リアルタイム同期
- 複数セッション間のキュー共有
- WebLLMの並列化（ハードウェア制約により不可能）

## Decisions

### 1. 並列/逐次処理モデル

**選択**: モードに応じた処理モデル
- **APIモード（オンライン）**: 並列処理、同時実行上限3件
- **WebLLMモード（オフライン）**: 逐次処理、1件ずつ

**理由**: 
- APIは独立したHTTPリクエストであり、サーバー側で並列処理される
- WebLLMはブラウザ内の単一GPUコンテキスト/モデルインスタンスを使用するため、並列処理は不可能

### 2. ジョブの状態遷移

```
queued → processing → completed/failed
```

複数ジョブが同時に`processing`状態になることが可能（APIモードの場合）。

**ジョブ型定義**:
```typescript
type QueuedJob = {
  id: string
  targetText: string
  status: 'queued' | 'processing' | 'completed' | 'failed'
  result?: SavedData
  error?: string
  queuedAt: Date
  completedAt?: Date
}
```

### 3. 並列処理の実装

**選択**: `Promise`ベースの並列リクエスト発行

```typescript
// APIモード: 並列処理
const MAX_CONCURRENT_API_JOBS = 3

// queuedジョブのうち、processingが上限未満なら新しいジョブを開始
const processingCount = jobQueue.filter(j => j.status === 'processing').length
const availableSlots = MAX_CONCURRENT_API_JOBS - processingCount
const jobsToStart = jobQueue
  .filter(j => j.status === 'queued')
  .slice(0, availableSlots)

// 各ジョブを独立して開始（awaitしない）
jobsToStart.forEach(job => startJobProcessing(job.id))
```

**WebLLMモード**: 上限を1件に設定し、逐次処理を強制

### 4. 通知の配置

**選択**: 既存`useToast`フックを活用し、右上に各ジョブの処理中/完了通知を表示

- 各ジョブ開始時: 「処理中: ジョブ #N」
- 各ジョブ完了時: 「完了: ジョブ #N」
- 複数ジョブが同時に処理中/完了してもそれぞれ個別に通知

### 5. 「確認」ボタンのセマンティクス

**選択**: 既存の`restoreFromHistory`ロジックを維持しつつ、ラベルと視覚的フィードバックを変更

**動作**:
1. 「確認」クリック → 履歴データを作業エリアにロード（既存動作）
2. ユーザーが確認・編集
3. 「確定してコピー・保存」 → 新しい履歴として保存 + 元エントリを「確認済み」にマーク

**確認済みステータス**: `SavedData`型に`confirmed: boolean`フィールドを追加

### 6. キュー処理中のUI状態

**選択**: ターゲットテキスト入力は常に有効、ボタンは常に「AI提案を生成」として機能（処理中でも新しいジョブを開始可能）

**UI表示**:
- 実行履歴セクションに複数の「処理中」ジョブを表示可能
- 各ジョブに進捗インジケータを表示

## Risks / Trade-offs

**[リスク] 並列リクエストによるAPI負荷** → 軽減: 同時実行上限（3件）を設定

**[リスク] キューが大きくなった場合のメモリ使用** → 軽減: キューサイズ上限（10件）を設定、超過時は警告表示

**[リスク] 処理中のセッション切り替え** → 軽減: 処理中のジョブがある場合はセッション切り替え時に確認ダイアログを表示

**[トレードオフ] WebLLMの逐次処理** → ハードウェア制約により回避不可能。ドキュメントで明記し、ユーザーにオンラインモード推奨を表示

**[トレードオフ] クライアント状態のみでの確認済みステータス管理** → ページリロードで確認状態は失われる。永続化はスコープ外とし、後続改善として検討

## Open Questions

- なし（並列処理の設計が明確化された）
