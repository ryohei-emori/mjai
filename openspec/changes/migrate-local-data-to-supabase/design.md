## Context

See proposal.md for motivation. 現状:
- ローカルSQLite (`backend/db/app.db`) に25セッション、291履歴、2018提案が存在
- Supabase Postgres に28セッション、290履歴、2018提案が既存
- 既存の `backend/db/migrate_local.py` はローカルPostgres向け（Supabase接続には `statement_cache_size=0` が必要）
- スキーマ差異: SQLite=PascalCase (Sessions, CorrectionHistories, AIProposals), Supabase=snake_case

## Goals / Non-Goals

**Goals:**
- SQLite内の欠落データをSupabaseへupsert
- 既存Supabaseデータを保護(上書きしない)
- Dry-run/Applyモードで安全に実行可能
- 冪等性のある移行(再実行しても問題なし)

**Non-Goals:**
- Supabase→SQLiteの逆同期
- スキーマ変更(既存のSupabaseスキーマはそのまま)
- 継続的な同期機構の構築(一回限りの移行)

## Decisions

### 1. Upsert戦略: INSERT ... ON CONFLICT DO NOTHING

**選択:** 主キー衝突時はスキップ (DO NOTHING)

**理由:**
- Supabaseが「新しい」データ(4セッションが追加済み)を持つため上書きは危険
- 欠落データの補完が目的であり、既存データの更新ではない
- 冪等性確保: 再実行しても同じ結果

**代替案:**
- `ON CONFLICT DO UPDATE`: 既存データを上書きするリスク
- `INSERT` のみ: 既存データで失敗する可能性

### 2. 無効参照の処理: スキップしてログ出力

**選択:** 外部キー参照が無効なレコードはスキップ

**理由:**
- `test-history-uuid`のような無効な参照を持つテストデータが存在
- FK制約違反でエラーになるよりスキップが安全
- ログで何がスキップされたか記録

### 3. 接続設定: statement_cache_size=0

**選択:** pgbouncer互換モードでSupabaseに接続

**理由:**
- Supabaseはpgbouncerをtransactionモードで使用
- prepared statementsがセッション間で共有されないため必須
- `DuplicatePreparedStatementError`を回避

### 4. ファイル配置: `backend/scripts/migrate_sqlite_to_supabase.py`

**選択:** scriptsディレクトリに新規作成

**理由:**
- 既存の `backend/db/migrate_local.py` はローカルPostgres向け
- 再利用ではなく専用スクリプトの方がシンプル
- 一回限りの移行ツールとして明確に分離

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Supabase接続エラー | Dry-runモードで事前確認。接続テスト失敗時は早期終了 |
| データ不整合 | FK順序を守る (sessions → histories → proposals)。無効参照はスキップ |
| 重複挿入 | ON CONFLICT DO NOTHING で冪等性確保 |
| 本番データ破損 | upsertは追加のみ、既存データに触れない。ロールバック不要 |

## Migration Plan

1. **Dry-run**: `python scripts/migrate_sqlite_to_supabase.py --dry-run`
   - SQLite内の欠落データを表示
   - Supabaseへの書き込みなし
2. **Apply**: `python scripts/migrate_sqlite_to_supabase.py --apply`
   - 欠落データをupsert
   - 結果サマリーを表示
3. **Verify**: スクリプト終了時に移行後のカウントを表示
4. **Document**: AGENTS.mdに移行完了ノートを追加
