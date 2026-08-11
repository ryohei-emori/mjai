## Context

現在の`page.tsx`は同期的なジョブ処理を行っており、`isProcessing`フラグで入力をブロックしている。`useToast`フックによるトースト通知は既に存在する。logoutボタンは`fixed top-4 right-4`に配置済み。

**重要**: クラウドAPI（`POST /api/suggestions` via Groq/Cloudflare）は本質的に並列リクエストをサポートしている。WebLLMのみが単一GPU/モデル制約により逐次処理を必要とする。

詳細はproposal.mdを参照。

## Goals / Non-Goals

**Goals:**
- クライアント側並列ジョブキュー実装（バックエンド変更不要）
- **APIモード**: 同時に複数リクエストを発行し、並列処理（上限: 30件）
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
- **APIモード（オンライン）**: 並列処理、同時実行上限30件
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
const MAX_CONCURRENT_API_JOBS = 30

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

### 7. 要確認（未確認）エントリのスタイリング

**選択**: ニュートラルグレー（`bg-gray-50`、`text-muted-foreground`）

**理由**:
- UI-DESIGN.mdにより、黄色（`bg-yellow-*`）は**警告（Warning）専用**
- 「要確認」は警告ではなく、処理完了後の通常ワークフロー状態
- ニュートラルグレーで「確認済み」との視覚的区別を維持しつつ、警告と誤解されない

## Risks / Trade-offs

**[リスク] 並列リクエストによるAPI負荷** → 軽減: 同時実行上限（30件）を設定。Groq無料枠などでは高並列時に429（レート制限）が発生しうるが、クライアント側フェイルオーバー（Cloudflare→WebLLM）で吸収可能であり、上限引き上げ自体はブロックしない

**[リスク] キューが大きくなった場合のメモリ使用** → 軽減: キューサイズ上限（10件）を設定、超過時は警告表示

**[リスク] 処理中のセッション切り替え** → 軽減: 処理中のジョブがある場合はセッション切り替え時に確認ダイアログを表示

**[トレードオフ] WebLLMの逐次処理** → ハードウェア制約により回避不可能。ドキュメントで明記し、ユーザーにオンラインモード推奨を表示

**[トレードオフ] クライアント状態のみでの確認済みステータス管理** → ページリロードで確認状態は失われる。永続化はスコープ外とし、後続改善として検討

## Open Questions

- なし（並列処理の設計が明確化された）

## Known Implementation Issues

~~以下の問題は設計どおりに実装されていない既知のバグでしたが、すべて修正済みです:~~

1. ~~**確認ボタンが動作しない**: `confirmJob`コールバックの依存配列に`updateCurrentSession`を追加して修正~~
2. ~~**オフラインモードOFF時にWebLLMが動作**: APIフェイルオーバー時のトースト通知を追加（仕様どおりの動作）~~
3. ~~**ターゲットテキストのクリア動作**: `handleGenerateClick`の依存配列を修正、ジョブ追加後にターゲットをクリア~~
4. ~~**要確認スタイリング**: 既に`bg-gray-50`で実装済み（黄色ではなくニュートラルグレー）~~

## HITL UI表示とクリックターゲット問題（追加）

### Issue A: AI修正提案UIが表示されない

**根本原因**: `confirmJob`内のスクロール処理が100msの`setTimeout`を使用しているが、Reactの再レンダリング完了前にタイムアウトが発生する場合がある。

**解決策**: タイムアウトベースのスクロールを`useEffect`に移動し、以下の条件でリアクティブに実行:
- `confirmingJobId`がセットされた時（ジョブキューからの確認）
- `currentSession.suggestions`が非空になった時

```typescript
// useEffect for reactive scroll to suggestions card
useEffect(() => {
  // Only scroll when confirming from job queue and suggestions are loaded
  if (confirmingJobId && currentSession?.suggestions.length > 0) {
    const suggestionsCard = document.querySelector('[data-suggestions-card]')
    if (suggestionsCard) {
      suggestionsCard.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }
}, [confirmingJobId, currentSession?.suggestions.length])
```

### Issue B: 確認ボタンのクリック範囲が狭い

**問題**: 完了ジョブカードの「確認」ボタンが小さく、ユーザーが正確にクリックする必要がある。

**解決策**: カード全体をクリック可能にし、UXを改善:
- 完了ステータスのカード全体に`onClick`を追加
- `cursor-pointer`で視覚的フィードバック
- アクセシビリティ対応（`role="button"`, `tabIndex`, キーボードハンドラー）
- 既存の「確認」ボタンスタイルは視覚的インジケーターとして維持

### 設計原則: 統一された確認UI

確認（confirm）操作は、トリガーソースに関わらず同一のAI修正提案レビューUIを表示すべき:
- ジョブキューからの確認 → AI修正提案カードを表示 + スクロール
- 実行履歴からの確認 → 同上
- 通常の生成フロー → 同上（スクロールは任意）

## 2026-08 `/opsx-apply` 追加分（要件4・5・6）

### Decision 8: 添削データのグルーピングキー

**調査結果**: `page.tsx`のコードを精査した結果、「添削データ」のグルーピングは**既に正しく実装されている**ことを確認した。`saveCorrections()`は呼び出しごとに厳密に1件の`SavedData`オブジェクトを生成し（`selectedCorrections`フィールドに採用した全提案を配列として保持）、`currentSession.savedData`配列にpushする。バックエンド側も対応して、1回の`saveCorrections()`実行につき1件の`correction_histories`行（`history_id`）が作成され、そのラウンドの全AI提案（選択・非選択問わず）が同じ`history_id`で`ai_proposals`テーブルに紐付く。`fetch_sessions()`の`correctionCount`も`COUNT(h.history_id)`（ラウンド数）でありAI提案数ではない。

**選択**: 既存のグルーピングキー（フロントエンド: `SavedData`オブジェクト1件 = 1ラウンド、バックエンド: `history_id`）を正式な設計上の不変条件として明文化する（spec.md参照）。加えて、この不変条件を壊しうる唯一の現実的なリスクとして「確定してコピー・保存」ボタンの二重クリック（非同期処理中の連打）によるラウンド重複を防ぐガードを追加する（`isSaving`状態でボタンを無効化）。

**判断根拠**: ユーザー報告の症状（「1ラウンドの複数採用が別々の`添削データ #N`として表示される」）を再現するコードパスは見つからなかった。既存の単体テスト・型定義からも、意図した設計は既にラウンド単位グルーピングである。実装上の追加バグではなく、二重送信という別のエッジケースが最も plausible な原因と判断し、そちらを防御的に修正した。

### Decision 9: エラーラウンドの再試行

**選択**: 失敗した特定のジョブをキューから削除し、同じターゲットテキストで`addJobAndProcess()`を再呼び出しする`retryJob()`関数を追加する。これにより既存の並列/逐次処理ロジック、同時実行上限、キューサイズ上限を含む全てのジョブ処理経路をそのまま再利用する。

**理由**: 新しいジョブとして再投入することで、既存の`processJobAsync`のオフライン/オンライン分岐、フォールバック処理、通知処理をすべてそのまま利用でき、専用の再試行パスを別途実装する必要がない。

### Decision 10: 「Saved」ステータス再訪バグの根本原因

**根本原因**: `loadSessionDetails()`内でバックエンドの`correction_histories`から`SavedData`を再構築する際、`confirmed`フィールドが設定されていなかった（未定義 = falsy）。バックエンドに永続化されている`correction_histories`行は、その存在自体が「ユーザーが確定・保存を実行した」ことを意味するため、復元時は常に`confirmed: true`であるべきだが、このフィールドが漏れていたため、セッション再訪時に全ての履歴エントリが「未確認」として表示されていた。

**修正**: `loadSessionDetails()`の`savedData.push(...)`に`confirmed: true`を追加。

**ラベル変更**: 「保存済み」（セッションヘッダーのバッジ）を英語の「Saved」に変更し、既存のブルータリストUI刷新で確立された英語ラベル規則（Session/History/Job Queue等）と統一する。実行履歴リスト内の確認済みエントリにも、色分けだけでなく明示的な「Saved」バッジを追加する。

## 2026-08 `/opsx-update /opsx-apply` 追加分（要件7・8: Historyカードのアーカイブ機能とクリック範囲拡大）

ユーザー報告のバグ2件: (1) 「添削データ #N」カードのゴミ箱アイコンが `onClick={() => console.log("削除機能未実装")}` という文字通りのno-opで機能していない、(2) チェックマークボタンの当たり判定が小さすぎて復元操作がしづらい。

### Decision 11: 削除ではなく「アーカイブ」（ソフトデリート）

**選択**: ゴミ箱ボタンを実装するにあたり、完全削除ではなく**アーカイブ**（ソフトデリート）として実装する。これは本コードベースの既存パターンと一致する: `backend/app/db_helper.py`の`delete_session()`は`UPDATE sessions SET status = 'archived'`を実行するソフトデリートであり、`DELETE /sessions/{session_id}`エンドポイントも`{"message": "Session archived", ...}`を返す。同様に、`correction_histories`テーブルに`is_archived BOOLEAN NOT NULL DEFAULT false`列を追加し（マイグレーション`004_add_history_archive.sql`）、個々の添削ラウンド単位でアーカイブできるようにする。

**理由**:
- セッション削除で確立済みのソフトデリート規約を、より粒度の細かい履歴ラウンド単位にも一貫して適用する
- 誤操作によるデータ完全消失を防ぐ（`ai_proposals`テーブルの関連提案データも`history_id`外部キー経由で保持され続ける）
- 将来的な「アーカイブ済み履歴の復元」機能の余地を残す（本変更のスコープ外）

**実装**:
- DB: `correction_histories.is_archived`列 + `(session_id, is_archived)`複合インデックス
- バックエンド: `DELETE /histories/{history_id}`エンドポイント（`db_helper.archive_history()`を呼び出し、`UPDATE ... SET is_archived = true`を実行）。`GET /sessions/{session_id}/histories`（`fetch_histories_by_session()`）はデフォルトで`WHERE is_archived = false`を適用し、アーカイブ済みラウンドを除外する。`fetch_sessions()`の`correctionCount`集計も同様に`is_archived = false`のみをカウントするよう統一する
- フロントエンド: `historyAPI.archiveHistory(historyId)`を追加。`SavedData`型に`historyId?: string`フィールドを追加し（`saveCorrections()`でのラウンド作成時、および`loadSessionDetails()`でのセッション再訪時の両方でバックエンドの`historyId`を保持）、アーカイブボタンのクリック時にこのIDでAPIを呼び出した上で、ローカル状態（`currentSession.savedData`）から楽観的に該当ラウンドを除去する
- UI: ゴミ箱アイコン（`delete`）をアーカイブアイコン（`archive`、Material Symbols）に変更し、トースト通知で「添削データをアーカイブしました」と表示。アーカイブ失敗時は既存のtry/catch + エラートーストパターンを踏襲する

### Decision 12: Historyカード全体のクリック可能化（Issue Bと同一パターンの再適用）

**選択**: 「添削データ #N」カードの外側`<div>`全体をクリック可能にし、既存の「確認」ボタンと同じ`restoreFromHistory(data); setConfirmingHistoryIndex(index)`をトリガーする。これは同ファイル内で既に適用済みのJob Queueカードのクリック範囲拡大（Issue B、Decision参照）と全く同じパターンである。

**実装**:
- カード外側の`<div>`に`onClick`（復元処理）、`cursor-pointer`、ホバー時のスタイル変更（`hover:bg-green-100`/`hover:border-md3-primary`、確認済み/未確認の状態に応じて既存のボーダー・背景色トークンを踏襲）、`role="button"`、`tabIndex={0}`、`onKeyDown`（Enter/Spaceキー対応）を追加
- カード内の「確認」ボタンと新しい「アーカイブ」ボタンの両方の`onClick`ハンドラーで`e.stopPropagation()`を呼び出し、ボタンクリックがカード全体のクリックイベントと二重発火しないようにする（Job Queueカードの`retryJob`ボタンと同一パターン）
- 「確認」ボタン自体は視覚的アフォーダンスとして維持する（冗長だが無害）
