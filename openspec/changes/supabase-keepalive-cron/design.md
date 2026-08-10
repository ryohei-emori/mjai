## Context

Supabase無料プランは約7日間アクティビティがないとプロジェクトを一時停止する。現在の `/health` エンドポイントはDBに接続しない軽量なもので、keep-alive用途には不十分。詳細な動機は proposal.md 参照。

本番環境はVercelモノレポデプロイ。APIは `/api/*` パスで提供される（`api/index.py` → `backend/app/main.py`）。

## Goals / Non-Goals

**Goals:**
- DBコネクションを含むkeep-aliveエンドポイント追加
- GitHub Actions cronによる自動定期実行
- ターゲットURL設定可能化（GitHub変数経由）
- 失敗時の可視化（ワークフロー失敗＋オプションでリトライ1回）

**Non-Goals:**
- Supabase Management APIの使用（不要な複雑性）
- 既存 `/health` エンドポイントの変更（用途が異なる）
- 複雑な監視・アラートシステム（GitHub Actions通知で十分）

## Decisions

### Decision 1: 専用 `/keepalive` エンドポイント vs `/health` 修正

**選択**: 新規 `/keepalive` エンドポイントを追加

**理由**:
- `/health` は「アプリが起動しているか」の確認用（Vercel/コンテナヘルスチェック）
- `/keepalive` は「DBがアクティブか」の確認用（Supabase keep-alive）
- 責務を分離することで既存のヘルスチェック動作に影響なし

**代替案**: `/health` にDBチェックを追加
- 却下理由: ヘルスチェックが遅くなり、DB障害時にアプリ全体が unhealthy 判定される

### Decision 2: 認証なし vs 認証あり

**選択**: 認証なしで公開

**理由**:
- エンドポイントは `SELECT 1` のみで、データアクセス・変更なし
- GitHub Actionsからのアクセスに認証設定が不要でシンプル
- 悪意のある大量アクセスはVercelのレート制限で対応可能

**代替案**: シークレットトークン認証
- 却下理由: 追加の複雑性に見合うセキュリティ上のメリットが薄い

### Decision 3: cronスケジュール頻度

**選択**: 3日ごと（`0 0 */3 * *`）

**理由**:
- Supabase free tierは約7日で停止 → 3日で十分な安全マージン
- GitHub Actionsの無料枠を考慮（月2000分）
- 1回の実行は数秒以下なので頻度を上げても問題ないが、必要性なし

**代替案**: 毎日実行
- 許容範囲だが過剰。ユーザーが望めば変数でカスタマイズ可能

### Decision 4: GitHub Actions変数 vs secret

**選択**: Repository variable (`KEEPALIVE_URL`)

**理由**:
- URLは機密情報ではない
- 変数の方が確認・変更が容易
- secretは認証トークンなど本当に機密のものに使用

## Risks / Trade-offs

**[エンドポイント悪用]** → Vercelレート制限で対応。深刻な場合はIP制限やシークレット認証を後から追加可能

**[GitHub Actions障害]** → Supabaseコンソールで手動pingまたはcurlで代替可能。重大な障害でなければ7日の猶予あり

**[ワークフロー通知見落とし]** → GitHubのwatch設定やSlack連携で対応（本changeのスコープ外）

## Migration Plan

1. `backend/app/main.py` に `/keepalive` エンドポイント追加
2. `.github/workflows/supabase-keepalive.yml` 作成
3. `AGENTS.md` にkeep-alive情報追記
4. mainブランチにマージ（Vercel自動デプロイ）
5. GitHub Actionsが次回スケジュールで自動実行開始
6. （オプション）手動でワークフローをトリガーして動作確認

ロールバック: ワークフローファイルを削除またはdisable。エンドポイントは残しても害なし。
