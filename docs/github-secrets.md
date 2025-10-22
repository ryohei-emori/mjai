# GitHub Secrets Configuration

以下のシークレットをGitHub Repositoryに設定する必要があります。

## インフラストラクチャ管理用シークレット

### Render
- `RENDER_API_KEY`
  - 説明: RenderのAPIキー
  - 取得方法: Renderダッシュボード → Account Settings → API Keys
  - 用途: RenderサービスのTerraform管理用

### Supabase
- `SUPABASE_ACCESS_TOKEN`
  - 説明: SupabaseのアクセストークN
  - 取得方法: Supabaseダッシュボード → Account → Access Tokens
  - 用途: SupabaseプロジェクトのTerraform管理用

- `SUPABASE_ORG_ID`
  - 説明: Supabase OrganizationのID
  - 取得方法: Supabaseダッシュボード → Organization Settings → General
  - 用途: プロジェクト作成時の所属Organization指定用

### Terraform（オプション）
- `TF_API_TOKEN`
  - 説明: Terraform CloudのAPIトークン
  - 取得方法: Terraform Cloud → User Settings → Tokens
  - 用途: tfstateのリモート管理用（Terraform Cloudを使用する場合）

## アプリケーション用シークレット

### Gemini AI
- `GEMINI_API_KEY`
  - 説明: Google Cloud GeminiのAPIキー
  - 取得方法: Google Cloud Console → APIとサービス → 認証情報
  - 用途: AIモデルへのアクセス用

- `GEMINI_MODEL`
  - 説明: 使用するGeminiモデルの指定
  - 値の例: "gemini-2.5-pro"
  - 用途: AIモデルの指定

## シークレットの設定方法

1. GitHubリポジトリに移動
2. Settings → Secrets and variables → Actions
3. "New repository secret"をクリック
4. 各シークレットの名前と値を入力

## 環境別の設定

本番環境と開発環境で異なる値を使用する場合：

1. GitHubリポジトリ → Settings → Environments
2. "New environment"で`staging`と`production`を作成
3. 環境ごとにシークレットを設定

## セキュリティ上の注意点

1. アクセストークンは定期的にローテーション
2. 本番環境のシークレットは必ずProtection rulesを設定
3. APIキーは必要最小限の権限のみを付与
4. シークレットの値をログ出力しない
5. Pull RequestのCI実行時は機密情報を隠蔽

## シークレットの更新手順

1. 新しいシークレットの生成
2. GitHubでの更新
3. 古いシークレットの無効化
4. アプリケーションの動作確認

## 緊急時の対応

シークレットが漏洩した場合：

1. 該当するシークレットを即座に無効化
2. 新しいシークレットを生成
3. GitHubシークレットを更新
4. インフラを再デプロイ
5. セキュリティ監査の実施