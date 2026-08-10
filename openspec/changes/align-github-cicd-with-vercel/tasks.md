## 1. CI Workflow作成

- [x] 1.1 `.github/workflows/ci.yml`を作成（backend pytest + frontend jest並列実行）
- [x] 1.2 CIワークフローのトリガーを設定（push to main, PRs to main）

## 2. 廃止ワークフロー削除

- [x] 2.1 `.github/workflows/deploy.yml`を削除

## 3. migrate-database.yml更新

- [x] 3.1 `backend/.github/workflows/migrate-database.yml`に警告コメントを追加
- [x] 3.2 ワークフロー名を"Database Migration (Manual Only)"に変更

## 4. AGENTS.md更新

- [x] 4.1 CI/CDセクションをVercel Git統合に合わせて書き換え
- [x] 4.2 GitHub Environments（Production / Preview / Staging）のマッピングを明記
- [x] 4.3 不要になったシークレット（RENDER_*, GEMINI_*）をドキュメントに記載
- [x] 4.4 新しいci.ymlワークフローを記載
