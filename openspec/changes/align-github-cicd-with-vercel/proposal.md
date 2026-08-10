## Why

GitHub Actionsの`deploy.yml`が廃止済みのRender/Terraformインフラを参照しており、現在のVercelモノレポデプロイアーキテクチャと矛盾している。CI/CDパイプラインを実際の運用（Vercel Git統合によるデプロイ、Supabase DBとAuth）に合わせて整理し、PRマージ前にテストを実行するCI workflowを追加する必要がある。

## What Changes

- **BREAKING**: `.github/workflows/deploy.yml`を廃止し、`ci.yml`（pytest + jest）に置き換え
- `backend/.github/workflows/migrate-database.yml`に警告コメントを追加（手動実行のみ維持）
- `AGENTS.md`のCI/CDセクションを現在のVercel環境（Production / Preview / Staging）に合わせて更新
- GitHub Secrets/Variablesのドキュメント更新（RENDER_*, GEMINI_*は不要）

## Capabilities

### New Capabilities
<!-- None - this is a pure infrastructure/documentation change -->

### Modified Capabilities
<!-- None - no spec-level behavior changes. This is CI/CD tooling and docs only. -->

This change is pure CI/CD infrastructure and documentation. No application behavior changes.
Setting `skip_specs: true` in `.openspec.yaml`.

## Impact

- **GitHub Actions**: `deploy.yml`が削除され、`ci.yml`が新規追加される
- **Documentation**: `AGENTS.md`のCI/CDセクションが更新される
- **GitHub Secrets**: `RENDER_API_KEY`, `RENDER_OWNER_ID`, `GEMINI_API_KEY`, `GEMINI_MODEL`は不要になる（削除は手動）
- **Vercel**: 変更なし（既にGit統合でデプロイ中）
- **コード**: 変更なし（テストは既存のものを実行）
