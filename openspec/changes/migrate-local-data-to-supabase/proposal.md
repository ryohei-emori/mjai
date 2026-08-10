## Why

ローカルSQLite (`backend/db/app.db`) に残っている過去のRender DB時代のデータをSupabaseへ移行する。AGENTSによるとRender DBは廃止済みでSupabaseが唯一のapp DBだが、ローカルSQLiteに歴史的データが残っている可能性があり、これを確認してSupabaseへマージする。

**調査結果:**
- SQLite: Sessions=25, CorrectionHistories=291, AIProposals=2018
- Supabase: sessions=28, correction_histories=290, ai_proposals=2018
- 差分: SQLiteのみに1セッション(`607b5c78-...`, 空のセッション、履歴なし)と1テストデータ履歴(`test-history-uuid`, 無効な参照)が存在
- 結論: 本番データは既にほぼ完全に移行済み。空セッションのみ補完移行が必要

## What Changes

- **新規**: SQLite→Supabase upsert移行スクリプト (`backend/scripts/migrate_sqlite_to_supabase.py`)
  - Dry-run モードで差分確認
  - Apply モードでupsert実行(主キーで重複スキップ)
  - 無効な外部キー参照を持つデータはスキップ
- **補完移行**: 欠落している空セッション1件をSupabaseへ追加
- **ドキュメント更新**: AGENTS.mdに移行完了ノート追加

## Capabilities

### New Capabilities

なし - これは一回限りのデータ移行ツールであり、アプリケーションの振る舞いは変更しない。

### Modified Capabilities

なし - 既存の spec レベルの要件変更はない。

**Note:** `skip_specs: true` を設定。純粋な運用・ツーリングタスクで、アプリの要件/振る舞い変更なし。

## Impact

- **コード**: `backend/scripts/migrate_sqlite_to_supabase.py` 新規作成
- **データ**: Supabaseに欠落セッション1件追加(空セッション、データ損失リスクなし)
- **依存関係**: asyncpg, python-dotenv (既存)
- **既存データへの影響**: upsert戦略により既存Supabaseデータは保護(上書きしない)
