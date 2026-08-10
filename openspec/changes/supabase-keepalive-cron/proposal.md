## Why

Supabaseの無料プランは一定期間（約7日）アクティビティがないとプロジェクトが一時停止する。これによりユーザーがアプリにアクセスした際にコールドスタート遅延や接続エラーが発生する可能性がある。定期的なkeep-aliveリクエストでDBを常時アクティブに保つ必要がある。

## What Changes

- 新しい `/keepalive` エンドポイントを追加（DBに `SELECT 1` を発行してコネクションプールを維持）
- GitHub Actions の scheduled cron ワークフローを追加（3〜4日ごとに本番URLへHTTPリクエスト）
- `KEEPALIVE_URL` をGitHub Actions変数として設定可能に（デフォルトは本番Vercel URL）
- `AGENTS.md` にSupabase無料プラン一時停止とkeep-aliveワークフローの存在を追記

## Capabilities

### New Capabilities
- `ops/supabase-keepalive`: Supabase DBのkeep-alive機能。スケジュールされた定期ping、認証不要のヘルスチェックエンドポイント、GitHub Actionsによる自動実行。

### Modified Capabilities
<!-- なし - 新規機能のみ -->

## Impact

- **Backend**: `backend/app/main.py` に認証不要の `/keepalive` エンドポイント追加
- **GitHub Actions**: `.github/workflows/supabase-keepalive.yml` 新規作成
- **Documentation**: `AGENTS.md` にkeep-alive運用情報を追記
- **Secrets/Variables**: GitHub repository variablesに `KEEPALIVE_URL` を追加（オプション）
