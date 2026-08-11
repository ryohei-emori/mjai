## 1. 型定義と状態管理の基盤

- [x] 1.1 `QueuedJob`型を定義（id, targetText, status, result, error, queuedAt, completedAt）
- [x] 1.2 `SavedData`型に`confirmed`フィールドを追加
- [x] 1.3 `jobQueue`状態（`useState<QueuedJob[]>`）を追加

## 2. 並列ジョブキュー処理ロジック

- [x] 2.1 キューにジョブを追加する`addJobAndProcess`関数を実装
- [x] 2.2 **APIモード並列処理**: 同時実行上限（30件）まで並列にジョブを開始するロジック実装
- [x] 2.3 **WebLLMモード逐次処理**: 単一ジョブのみ処理する逐次ロジック維持
- [x] 2.4 各ジョブの独立した処理完了ハンドリング（Promise.thenベース）
- [x] 2.5 処理完了時にジョブをcompletedに更新し、結果を実行履歴に反映

## 3. UIラベル変更

- [x] 3.1 「保存履歴」→「実行履歴」にCardTitleを変更
- [x] 3.2 「復元」ボタン→「確認」ボタンにラベル変更
- [x] 3.3 ボタンアイコンを`RotateCcw`から`CheckCircle`に変更

## 4. 右上ステータス通知

- [x] 4.1 処理開始時にジョブごとの「処理中」トースト通知を表示
- [x] 4.2 ジョブ完了時にジョブごとの「完了」トースト通知を表示
- [x] 4.3 キュー内のジョブ数をトーストに含める

## 5. HITL確認フロー

- [x] 5.1 `confirmJob`関数を実装（ジョブ結果をワークエリアにロード）
- [x] 5.2 確認済みエントリの視覚的区別（バッジまたは背景色）を実装
- [x] 5.3 `saveCorrections`実行時に元エントリを`confirmed: true`に更新

## 6. キュー制御UI

- [x] 6.1 ボタンは常に「AI提案を生成」（処理中/待機数をバッジで表示）
- [x] 6.2 キューサイズ上限（10件）チェックと警告表示を実装
- [x] 6.3 ジョブキューセクションで複数の「処理中」ジョブを表示

## 7. 検証とクリーンアップ

- [x] 7.1 並列処理モード表示（APIモード vs WebLLMモード）
- [x] 7.2 セッション切り替え時の処理中ジョブ確認ダイアログ実装
- [x] 7.3 リンターエラーの確認と修正
- [x] 7.4 不要なコード削除（generateAISuggestions、isProcessing状態など）

## 8. 既知のバグ（次回 `/opsx-apply` 対象）

以下は実装完了済みタスクに関する既知のバグ。計画artifacts上は正しく定義されているが、実装が仕様と乖離している。

- [x] 8.1 **確認ボタン動作不良**: 完了ジョブの「確認」クリックで結果がワークスペースにロードされない
- [x] 8.2 **オフラインモードOFF時のパス誤り**: トグルOFFでもWebLLMが動作するケースがある（正: クラウドAPI使用）
- [x] 8.3 **要確認スタイリング**: 黄色ではなくニュートラルグレー（`bg-gray-50`）を使用するよう修正
- [x] 8.4 **ジョブキュー追加後のターゲットクリア**: 新ジョブ追加後、ターゲットテキスト入力欄の状態を明確化

## 9. HITL確認UI表示問題

- [x] 9.1 **確認ボタンでHITL UIが表示されない**: `confirmJob`でsuggestionsをセッションにロードしているが、AI修正提案カード（どこを/どのように）が表示されない問題を修正
  - 原因: `confirmJob`後にスクロール位置が変わらない、または状態更新が正しく反映されていない可能性
  - 修正: 
    - `confirmingJobId`状態を追加してジョブキューからの確認を追跡
    - suggestionsが空の場合のエラーハンドリングを追加
    - AI提案カードに`data-suggestions-card`属性を追加し、確認後に自動スクロール
    - 確認完了後にジョブをキューから削除
    - AI修正提案カードに「確認中」バッジを表示

## 10. HITL確認UIが依然として表示されない問題（Issue A）

- [x] 10.1 **根本原因**: `confirmJob`のスクロール処理で100msタイムアウトがReactの再レンダリング完了前に実行される
  - 症状: 確認ボタンクリック後、AI修正提案カードが表示されない（状態は正しく設定されているが、UIに反映されない/スクロールされない）
  - 修正:
    - スクロール処理を`useEffect`に移動し、`suggestions`状態変更を検知して実行
    - `confirmingJobId`がセットされた時のみスクロールを実行（通常の生成フローと区別）
    - タイムアウトベースのスクロールをリアクティブなuseEffectに置き換え

- [x] 10.2 **設計原則の明文化**: 確認（confirm）は常に共有の提案レビューUIをトリガーすべき
  - ジョブキューからの確認も実行履歴からの確認も、同一のAI修正提案セクションを表示
  - トリガーソース（ジョブキュー vs 履歴）に関わらず、同じUI/UXを提供

## 11. ジョブカードのクリックターゲット問題（Issue B）

- [x] 11.1 **確認ボタンのクリック範囲が狭い**: 完了ジョブカード全体をクリック可能に
  - 現状: 小さな「確認」ボタンのみがクリック可能
  - 修正:
    - カード全体に`onClick`を追加し、確認処理をトリガー
    - `cursor-pointer`を追加して視覚的にクリック可能であることを示す
    - ボタンの視覚的スタイルは維持（ユーザーにアクションポイントを示す）
    - ネストされたインタラクティブ要素の問題を回避（ボタンではなくdivとして実装）
    - アクセシビリティ: `role="button"` + `tabIndex={0}` + キーボードハンドラー

## 12. 添削データのグルーピング検証・エラー再試行・Savedステータス修正（2026-08 `/opsx-apply`、要件4・5・6）

- [x] 12.1 **要件4調査**: `saveCorrections()` / `loadSessionDetails()` / `db_helper.py`のグルーピングロジックを精査 — 既に`SavedData`1件=1ラウンド（`history_id`単位）で正しくグルーピングされていることを確認（design.md Decision 8参照）
- [x] 12.2 **要件4防御的修正**: `saveCorrections()`に`isSaving`状態を追加し、二重クリック/連続送信による重複ラウンド作成を防止
- [x] 12.3 **要件4ドキュメント化**: グルーピングキー（`SavedData`/`history_id`）をspec.md/design.mdに不変条件として明文化
- [x] 12.4 **要件5**: `retryJob(job)`関数を実装 — 失敗ジョブをキューから削除し、同一ターゲットテキストで`addJobAndProcess()`を再呼び出し
- [x] 12.5 **要件5 UI**: ジョブキュー内の`failed`ステータスのジョブカードに再試行ボタンを追加
- [x] 12.6 **要件6根本原因修正**: `loadSessionDetails()`の`savedData.push(...)`に`confirmed: true`を追加し、セッション再訪時に既存履歴が「未確認」と誤表示される回帰バグを修正
- [x] 12.7 **要件6ラベル変更**: セッションヘッダーの「保存済み: N件」バッジを「Saved: N」に変更
- [x] 12.8 **要件6 UI強化**: 実行履歴（History）リスト内の確認済みエントリに、背景色だけでなく明示的な「Saved」バッジを追加
- [x] 12.9 **ドキュメント更新**: `docs/UI-DESIGN.md`に「保存済み」の記載がないか確認（確認済み: 記載なし、変更不要）
- [x] 12.10 `npm run lint` / `npm run build`でリグレッションがないことを確認

## 13. Historyカードのアーカイブ機能とクリック範囲拡大（2026-08 `/opsx-update /opsx-apply`、要件7・8）

- [x] 13.1 **DBマイグレーション**: `backend/supabase/migrations/004_add_history_archive.sql`を追加し、`correction_histories`に`is_archived BOOLEAN NOT NULL DEFAULT false`列 + `(session_id, is_archived)`インデックスを追加。`conf/.env`の`DATABASE_URL`が指す本番Supabase Postgresに`asyncpg`経由で直接適用し、`information_schema.columns`で列の存在を確認
- [x] 13.2 **バックエンド`db_helper.py`**: `archive_history(history_id)`関数を追加（`delete_session()`と同じソフトデリートパターンで`UPDATE correction_histories SET is_archived = true`）。`fetch_histories_by_session()`に`AND is_archived = false`条件を追加し、アーカイブ済みラウンドをデフォルトで除外。`fetch_sessions()`の`correctionCount`集計も`COUNT(h.history_id) FILTER (WHERE h.is_archived = false)`に変更し一貫性を保つ
- [x] 13.3 **バックエンド`main.py`**: `DELETE /histories/{history_id}`エンドポイントを追加し、`archive_history()`を呼び出して`{"message": "History archived", "historyId": history_id}`を返す（`DELETE /sessions/{session_id}`と同じレスポンス形式）
- [x] 13.4 **フロントエンド`api.ts`**: `historyAPI.archiveHistory(historyId)`を追加し、新エンドポイントを呼び出す
- [x] 13.5 **フロントエンド`page.tsx`型定義**: `SavedData`型に`historyId?: string`を追加し、`saveCorrections()`の2箇所（ジョブキュー確認フロー・新規保存フロー）と`loadSessionDetails()`の両方で`historyId`を設定
- [x] 13.6 **フロントエンド`page.tsx`アーカイブボタン**: ゴミ箱ボタンの`onClick={() => console.log("削除機能未実装")}`という文字通りのno-opを、`archiveHistoryRound(data, index)`関数（`historyAPI.archiveHistory()`呼び出し→ローカル`savedData`から楽観的除去→トースト表示、try/catchでエラートースト）に置き換え。アイコンを`delete`から`archive`に変更
- [x] 13.7 **フロントエンド`page.tsx`カード全体クリック化**: 「添削データ #N」カードの外側`<div>`に、Job Queueカードと同じパターン（`onClick`＋`cursor-pointer`＋ホバースタイル＋`role="button"`＋`tabIndex={0}`＋`onKeyDown`）で復元処理（`restoreFromHistory` + `setConfirmingHistoryIndex`）を追加。既存の「確認」ボタンと新しいアーカイブボタンの両方に`e.stopPropagation()`を追加し、カードクリックとの二重発火を防止
- [x] 13.8 **OpenSpecドキュメント更新**: design.md（Decision 11・12）とspec.md（アーカイブ要件・カード全体クリック要件）に本変更を明文化
- [x] 13.9 **テスト**: `backend/tests/test_history_archive.py`を新規追加（`test_session_archive.py`のパターンをミラー）。DELETE エンドポイントのアーカイブ動作、`GET /histories`のアーカイブ除外、`db_helper`関数がUPDATE（DELETE ではない）を使うこと、SQLクエリに`is_archived = false`条件があることを検証
- [x] 13.10 `npm run lint`でリグレッションがないことを確認
