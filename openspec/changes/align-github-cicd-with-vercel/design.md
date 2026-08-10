## Context

現在のCI/CD状態:
- `.github/workflows/deploy.yml`: Render/Terraformへのデプロイ（廃止済みインフラ）
- `.github/workflows/supabase-keepalive.yml`: Supabase keep-alive（正常動作中）
- `backend/.github/workflows/migrate-database.yml`: 手動DBマイグレーション

実際のインフラ:
- **デプロイ**: Vercel Git統合（main → Production、PR → Preview）
- **DB/Auth**: Supabase
- **AI**: クライアントサイドWebLLM（Gemini不要）
- **GitHub Environments**: `production`, `staging`, `Preview`（Vercel UIで確認済み）

See proposal.md for motivation.

## Goals / Non-Goals

**Goals:**
- PR/push時にbackend pytest + frontend jestを実行し、マージ前にテスト失敗を検出
- Vercel Git統合によるデプロイフローを明確にドキュメント化
- 廃止済みのRender/Terraform参照を削除
- AGENTS.mdを現在のCI/CD実態に合わせて更新

**Non-Goals:**
- Vercelダッシュボード設定の変更（既に正しく設定済み）
- GitHub Secrets/Variablesの自動削除（手動で対応）
- staging環境の新規構築（既存のPreview環境で十分）
- terraform/ディレクトリの削除（将来の参照用に保持）

## Decisions

### 1. deploy.ymlをci.ymlに置き換える

**選択**: Render/Terraformデプロイを削除し、テスト専用CIに変換

**理由**:
- デプロイはVercel Git統合が処理するため、GitHub Actionsでのデプロイは不要
- PRマージ前のテスト実行によりコード品質を維持

**代替案**:
- deploy.ymlを無効化するだけ → 混乱の原因になるため却下
- Vercel CLIでデプロイ → Git統合の方がシンプルで推奨

### 2. CIワークフローの構成

**選択**: 単一の`ci.yml`でbackend + frontendテストを並列実行

```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  backend-test:
    # Python 3.12, pytest
  frontend-test:
    # Node 20, npm ci, jest
  lint:
    # eslint + ruff (optional, continue-on-error)
```

**理由**:
- 並列実行で高速化
- 単一ファイルで管理が容易
- lintは警告のみ（既存コードにlintエラーがある可能性）

### 3. Staging環境の扱い

**選択**: GitHub Environment `staging`は保持するが、専用ブランチやワークフローは追加しない

**理由**:
- VercelのPreview環境がPRごとのステージング機能を提供
- 専用stagingブランチのメンテナンスコストを回避
- 必要に応じて将来追加可能

**ドキュメント化**:
- Production: `main`ブランチへのpushで自動デプロイ
- Preview: PRごとに自動デプロイ（stagingとして使用可能）
- Staging: GitHub Environment存在するが、現在未使用（将来用）

### 4. migrate-database.ymlの扱い

**選択**: 手動実行のみ維持し、警告コメントを追加

**理由**:
- ライブデータ移行は危険なため自動実行すべきでない
- 既存のworkflow_dispatchトリガーは適切
- 名前を`migrate-database.yml`のまま維持（移動不要）

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| CIテストがローカル環境と異なる挙動 | pytest/jestはローカルと同じコマンドを使用、DB依存テストはモック済み |
| Lintエラーで既存PRがブロック | lint jobは`continue-on-error: true`で警告のみに |
| GitHub Secretsの古いエントリが残る | ドキュメントに削除可能なシークレットを明記（手動対応） |
| deploy.yml削除でデプロイが止まる | Vercel Git統合は既に動作中のため影響なし |

## Migration Plan

1. `ci.yml`を作成してpush（deploy.ymlと共存可能）
2. CIが正常動作することを確認
3. `deploy.yml`を削除
4. `migrate-database.yml`に警告コメントを追加
5. `AGENTS.md`を更新
6. READMEは必要に応じてAGENTS.mdを参照するよう軽微な更新

**Rollback**: deploy.ymlの削除はgit revertで復元可能（ただしRenderは既に停止済みのため復元しても動作しない）
