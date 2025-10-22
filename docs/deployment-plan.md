# MJAI デプロイ計画書

## 概要

このドキュメントは、MJAIアプリケーションをSupabase（データベース）とRender（フロントエンド・バックエンド）にデプロイするための包括的な計画書です。

## アーキテクチャ構成

```
┌─────────────────────────────────────────────────────────────┐
│                         ユーザー                              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Render (Frontend - Next.js)                     │
│              https://mjai-frontend.onrender.com              │
└────────────────────┬────────────────────────────────────────┘
                     │ API呼び出し
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Render (Backend - FastAPI)                      │
│              https://mjai-backend.onrender.com               │
└────────────────────┬────────────────────────────────────────┘
                     │ DB接続
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Supabase (PostgreSQL)                           │
│              db.fqyhrubqkpuyliqojbai.supabase.co            │
└─────────────────────────────────────────────────────────────┘
```

## デプロイフェーズ

### Phase 1: 事前準備（完了済み）
- [x] Supabaseプロジェクト作成
- [x] データベーススキーマ作成
- [x] SQLiteからSupabaseへのデータ移行
- [x] 環境変数の整理

### Phase 2: インフラストラクチャのセットアップ
- [ ] GitHub Secretsの設定
- [ ] Terraform設定の確認と調整
- [ ] Renderアカウントの準備

### Phase 3: バックエンドのデプロイ
- [ ] Renderバックエンドサービスの作成
- [ ] 環境変数の設定
- [ ] ヘルスチェックの確認
- [ ] API動作テスト

### Phase 4: フロントエンドのデプロイ
- [ ] Renderフロントエンドサービスの作成
- [ ] ビルド設定の確認
- [ ] 環境変数の設定
- [ ] 動作確認

### Phase 5: 統合テストと本番化
- [ ] エンドツーエンドテスト
- [ ] パフォーマンステスト
- [ ] セキュリティチェック
- [ ] 監視設定

## 詳細手順

---

## Phase 2: インフラストラクチャのセットアップ

### 2.1 GitHub Secretsの設定

GitHubリポジトリ（Settings → Secrets and variables → Actions）に以下のシークレットを設定：

#### 必須シークレット

| シークレット名 | 説明 | 取得方法 |
|--------------|------|---------|
| `RENDER_API_KEY` | RenderのAPIキー | Render Dashboard → Account Settings → API Keys |
| `SUPABASE_ACCESS_TOKEN` | Supabaseアクセストークン | Supabase Dashboard → Account → Access Tokens |
| `SUPABASE_PROJECT_REF` | Supabaseプロジェクト参照ID | Supabase Dashboard → Project Settings → General |
| `SUPABASE_ORG_ID` | Supabase組織ID | Supabase Dashboard → Organization Settings |
| `GEMINI_API_KEY` | Gemini APIキー | Google Cloud Console → APIs & Services → Credentials |
| `GEMINI_MODEL` | 使用するGeminiモデル | 例: `gemini-2.5-flash` |

#### オプションシークレット

| シークレット名 | 説明 | 用途 |
|--------------|------|------|
| `TF_API_TOKEN` | Terraform Cloudトークン | tfstateのリモート管理（使用する場合） |

### 2.2 Terraform設定の確認

#### 現在のTerraform構成の問題点

`terraform/main.tf`を確認したところ、以下の問題があります：

1. **Supabaseプロバイダーの使用**
   - 現在のTerraformはSupabaseプロジェクトを作成しようとしていますが、既にSupabaseプロジェクトは作成済みです
   - Supabase Terraform Providerは実験的で、既存プロジェクトの管理には向いていません

2. **テーブルスキーマの定義**
   - Terraformでテーブルを定義していますが、実際のアプリケーションスキーマと異なります
   - 既にSupabase上にスキーマは作成済みです

#### 推奨される修正

Terraformの役割を以下に限定します：
- Renderサービス（フロントエンド・バックエンド）の管理のみ
- Supabaseは既存プロジェクトを使用（Terraform管理外）

修正版の`terraform/main.tf`を作成します。

### 2.3 Renderアカウントの準備

1. [Render](https://render.com)にアクセスしてアカウント作成
2. GitHubアカウントと連携
3. API Keyを生成（Dashboard → Account Settings → API Keys）
4. GitHub Secretsに`RENDER_API_KEY`を設定

---

## Phase 3: バックエンドのデプロイ

### 3.1 バックエンドの構成確認

#### 必要な環境変数

```env
# データベース接続
DATABASE_URL=postgresql://postgres.fqyhrubqkpuyliqojbai:PASSWORD@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres

# アプリケーション設定
ENVIRONMENT=production
USE_POSTGRESQL=true
APP_ROOT=/app
PYTHONPATH=/app

# Gemini API
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash

# CORS設定
FRONTEND_URL=https://mjai-frontend.onrender.com
```

#### Dockerfileの確認

`backend/Dockerfile`は既に本番環境対応済み：
- ✅ 非rootユーザーで実行
- ✅ ヘルスチェック設定済み
- ✅ ポート環境変数対応（`${PORT:-8000}`）

#### 起動コマンド

```bash
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

### 3.2 Renderバックエンドサービスの作成

#### 手動作成の場合

1. Render Dashboard → "New +" → "Web Service"
2. GitHubリポジトリを選択：`ryohei-emori/mjai`
3. 以下の設定を入力：

```yaml
Name: mjai-backend
Region: Oregon (US West)
Branch: main
Root Directory: backend
Runtime: Docker
Docker Command: (空欄 - Dockerfileのデフォルトを使用)
Plan: Starter ($7/month) または Free
```

4. 環境変数を設定（上記3.1参照）
5. "Create Web Service"をクリック

#### Terraform経由の場合

修正版の`terraform/main.tf`を使用して自動作成（後述）

### 3.3 デプロイ後の確認

#### ヘルスチェック

```bash
curl https://mjai-backend.onrender.com/health
# 期待される応答: {"status":"healthy","message":"Application is running"}
```

#### API動作確認

```bash
# セッション一覧取得
curl https://mjai-backend.onrender.com/sessions

# 期待される応答: セッションの配列（空配列または既存データ）
```

#### ログ確認

Render Dashboard → mjai-backend → Logs タブでログを確認

---

## Phase 4: フロントエンドのデプロイ

### 4.1 フロントエンドの構成確認

#### 必要な環境変数

```env
# ビルド時に必要（NEXT_PUBLIC_*）
NEXT_PUBLIC_API_URL=https://mjai-backend.onrender.com

# Node.js設定
NODE_VERSION=20
NODE_ENV=production
PORT=8080
```

#### Dockerfileの確認

`frontend/Dockerfile`は既にマルチステージビルド対応済み：
- ✅ 依存関係の最適化
- ✅ Standalone出力モード
- ✅ 非rootユーザーで実行

#### next.config.jsの確認

`frontend/next.config.js`は既に本番環境対応済み：
- ✅ `output: 'standalone'` 設定済み
- ✅ 環境変数の読み込み対応

### 4.2 Renderフロントエンドサービスの作成

#### 手動作成の場合

1. Render Dashboard → "New +" → "Web Service"
2. GitHubリポジトリを選択：`ryohei-emori/mjai`
3. 以下の設定を入力：

```yaml
Name: mjai-frontend
Region: Oregon (US West)
Branch: main
Root Directory: frontend
Runtime: Docker
Docker Command: (空欄 - Dockerfileのデフォルトを使用)
Plan: Starter ($7/month) または Free
```

4. 環境変数を設定：
   - `NEXT_PUBLIC_API_URL`: `https://mjai-backend.onrender.com`
   - `NODE_ENV`: `production`
   - `PORT`: `8080`

5. "Create Web Service"をクリック

#### Terraform経由の場合

修正版の`terraform/main.tf`を使用して自動作成（後述）

### 4.3 デプロイ後の確認

#### アクセステスト

ブラウザで`https://mjai-frontend.onrender.com`にアクセス

#### 機能確認

1. セッション一覧が表示されるか
2. 新しいセッションを作成できるか
3. 翻訳校閲機能が動作するか
4. データがSupabaseに保存されるか

---

## Phase 5: 統合テストと本番化

### 5.1 エンドツーエンドテスト

#### テストシナリオ

1. **セッション管理**
   - [ ] セッション一覧の取得
   - [ ] 新規セッションの作成
   - [ ] セッション名の変更
   - [ ] セッションの削除

2. **翻訳校閲**
   - [ ] 原文と訳文の入力
   - [ ] AI提案の生成（Gemini API）
   - [ ] 提案の選択と保存
   - [ ] 履歴の表示

3. **データ永続化**
   - [ ] ページリロード後もデータが保持される
   - [ ] 複数セッション間でのデータ分離

### 5.2 パフォーマンステスト

#### 目標値

| 指標 | 目標 |
|------|------|
| ページ読み込み時間 | < 3秒 |
| API応答時間 | < 500ms |
| AI提案生成時間 | < 10秒 |

#### 測定方法

```bash
# API応答時間
time curl https://mjai-backend.onrender.com/sessions

# ページ読み込み時間
# Chrome DevTools → Network タブで確認
```

### 5.3 セキュリティチェック

#### チェックリスト

- [ ] 環境変数が適切に設定されている（ハードコードなし）
- [ ] CORS設定が適切（本番URLのみ許可）
- [ ] HTTPSが有効（Renderはデフォルトで有効）
- [ ] APIキーが暗号化されている
- [ ] データベース接続がSSL経由

#### CORS設定の確認

`backend/app/main.py`のCORS設定を本番環境用に調整：

```python
if os.environ.get("ENVIRONMENT", "development") == "production":
    cors_origins = [
        os.environ.get("FRONTEND_URL"),  # https://mjai-frontend.onrender.com
        "https://*.onrender.com"
    ]
```

### 5.4 監視設定

#### Renderの監視機能

1. **ヘルスチェック**
   - バックエンド: `/health` エンドポイント
   - 自動的に30秒ごとにチェック

2. **アラート設定**
   - Render Dashboard → Service → Settings → Notifications
   - デプロイ失敗時のメール通知を有効化

3. **ログ監視**
   - Render Dashboard → Service → Logs
   - エラーログの定期確認

#### Supabaseの監視

1. **データベース使用量**
   - Supabase Dashboard → Settings → Usage
   - 無料プランの制限を監視

2. **接続数**
   - Supabase Dashboard → Database → Connection Pooling
   - 接続プールの使用状況を確認

---

## Terraform自動デプロイ

### 修正版terraform/main.tf

既存のSupabaseプロジェクトを使用し、Renderサービスのみを管理する構成：

```hcl
terraform {
  required_providers {
    render = {
      source  = "render-oss/render"
      version = "~> 1.3.0"
    }
  }
  required_version = ">= 1.0.0"
}

provider "render" {
  api_key = var.render_api_key
}

############################
# Backend service
############################
resource "render_service" "backend" {
  name            = "${var.project_name}-backend"
  region          = var.render_region
  repo_url        = "https://github.com/${var.repo}"
  branch          = var.branch
  service_type    = "web_service"
  plan            = var.backend_plan
  root_directory  = "backend"
  runtime         = "docker"

  # 環境変数
  env_vars = [
    {
      key   = "DATABASE_URL"
      value = var.database_url
    },
    {
      key   = "ENVIRONMENT"
      value = var.environment
    },
    {
      key   = "USE_POSTGRESQL"
      value = "true"
    },
    {
      key   = "APP_ROOT"
      value = "/app"
    },
    {
      key   = "PYTHONPATH"
      value = "/app"
    },
    {
      key   = "GEMINI_API_KEY"
      value = var.gemini_api_key
    },
    {
      key   = "GEMINI_MODEL"
      value = var.gemini_model
    },
    {
      key   = "FRONTEND_URL"
      value = "https://${var.project_name}-frontend.onrender.com"
    }
  ]

  # ヘルスチェック
  health_check_path = "/health"
  
  # 自動デプロイ
  auto_deploy = true
}

############################
# Frontend service
############################
resource "render_service" "frontend" {
  name            = "${var.project_name}-frontend"
  region          = var.render_region
  repo_url        = "https://github.com/${var.repo}"
  branch          = var.branch
  service_type    = "web_service"
  plan            = var.frontend_plan
  root_directory  = "frontend"
  runtime         = "docker"

  # 環境変数
  env_vars = [
    {
      key   = "NEXT_PUBLIC_API_URL"
      value = render_service.backend.service_url
    },
    {
      key   = "NODE_ENV"
      value = "production"
    },
    {
      key   = "PORT"
      value = "8080"
    }
  ]

  # 自動デプロイ
  auto_deploy = true

  # バックエンドが先にデプロイされる
  depends_on = [render_service.backend]
}
```

### 修正版terraform/variables.tf

```hcl
variable "render_api_key" {
  type        = string
  description = "Render API key"
  sensitive   = true
}

variable "project_name" {
  type        = string
  description = "Project name prefix"
  default     = "mjai"
}

variable "repo" {
  type        = string
  description = "GitHub repo (owner/repo)"
  default     = "ryohei-emori/mjai"
}

variable "branch" {
  type        = string
  description = "Git branch to deploy"
  default     = "main"
}

variable "render_region" {
  type        = string
  description = "Render deployment region"
  default     = "oregon"
}

variable "environment" {
  type        = string
  description = "Environment name"
  default     = "production"
}

variable "frontend_plan" {
  type        = string
  description = "Render plan for frontend"
  default     = "starter"
}

variable "backend_plan" {
  type        = string
  description = "Render plan for backend"
  default     = "starter"
}

variable "database_url" {
  type        = string
  description = "Supabase database connection URL"
  sensitive   = true
}

variable "gemini_api_key" {
  type        = string
  description = "Gemini API key"
  sensitive   = true
}

variable "gemini_model" {
  type        = string
  description = "Gemini model identifier"
  default     = "gemini-2.5-flash"
}
```

### Terraform実行手順

#### ローカルでの実行

```bash
# 1. 環境変数の設定
export TF_VAR_render_api_key="your_render_api_key"
export TF_VAR_database_url="postgresql://postgres.fqyhrubqkpuyliqojbai:PASSWORD@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres"
export TF_VAR_gemini_api_key="your_gemini_api_key"

# 2. Terraform初期化
terraform -chdir=terraform init

# 3. プラン確認
terraform -chdir=terraform plan

# 4. 適用
terraform -chdir=terraform apply
```

#### GitHub Actions経由の実行

`.github/workflows/terraform.yml`を使用：

```bash
# 手動トリガー
# GitHub → Actions → Infrastructure Deployment → Run workflow
```

---

## コスト見積もり

### 無料プランの場合

| サービス | プラン | 月額 | 制限 |
|---------|-------|------|------|
| Render Backend | Free | $0 | 750時間/月、スリープあり |
| Render Frontend | Free | $0 | 750時間/月、スリープあり |
| Supabase | Free | $0 | 500MB、2プロジェクト |
| **合計** | | **$0** | |

**注意**: 無料プランは15分間アクセスがないとスリープします。

### 有料プランの場合（推奨）

| サービス | プラン | 月額 | 特徴 |
|---------|-------|------|------|
| Render Backend | Starter | $7 | スリープなし、512MB RAM |
| Render Frontend | Starter | $7 | スリープなし、512MB RAM |
| Supabase | Free | $0 | 十分な容量 |
| **合計** | | **$14** | |

---

## トラブルシューティング

### よくある問題と解決方法

#### 1. データベース接続エラー

**症状**: `asyncpg.exceptions.InvalidPasswordError`

**解決方法**:
- DATABASE_URLの形式を確認
- パスワードに特殊文字がある場合はURLエンコード
- Supabaseのファイアウォール設定を確認

```bash
# 正しい形式
postgresql://postgres.PROJECT_REF:PASSWORD@aws-0-REGION.pooler.supabase.com:6543/postgres
```

#### 2. CORSエラー

**症状**: フロントエンドからAPIを呼び出すと`CORS policy`エラー

**解決方法**:
- バックエンドの`FRONTEND_URL`環境変数を確認
- `backend/app/main.py`のCORS設定を確認

```python
cors_origins = [
    os.environ.get("FRONTEND_URL"),  # 正しいURLが設定されているか確認
]
```

#### 3. ビルドエラー

**症状**: Renderでのビルドが失敗

**解決方法**:
- Dockerfileの構文を確認
- 依存関係のバージョンを確認
- Renderのログを詳細に確認

```bash
# ローカルでDockerビルドをテスト
docker build -t mjai-backend ./backend
docker build -t mjai-frontend ./frontend
```

#### 4. 環境変数が反映されない

**症状**: アプリケーションが環境変数を読み込めない

**解決方法**:
- Renderダッシュボードで環境変数を確認
- サービスを再起動
- ログで環境変数の値を確認（機密情報は除く）

---

## デプロイチェックリスト

### デプロイ前

- [ ] GitHub Secretsが全て設定されている
- [ ] Supabaseにデータが移行されている
- [ ] ローカルでDockerビルドが成功する
- [ ] 環境変数が整理されている

### デプロイ中

- [ ] Renderバックエンドサービスが作成された
- [ ] バックエンドのヘルスチェックが成功
- [ ] Renderフロントエンドサービスが作成された
- [ ] フロントエンドがビルド成功

### デプロイ後

- [ ] フロントエンドにアクセスできる
- [ ] バックエンドAPIが応答する
- [ ] データベース接続が確立されている
- [ ] セッション作成・取得が動作する
- [ ] AI提案生成が動作する
- [ ] ログにエラーがない

---

## 次のステップ

### 短期（1週間以内）

1. 手動でRenderサービスを作成してデプロイ
2. 基本的な動作確認
3. 問題があれば修正

### 中期（1ヶ月以内）

1. Terraformでの自動デプロイに移行
2. CI/CDパイプラインの整備
3. 監視・アラートの設定

### 長期（3ヶ月以内）

1. カスタムドメインの設定
2. CDNの導入
3. パフォーマンス最適化
4. スケーリング戦略の検討

---

## 参考リンク

- [Render Documentation](https://render.com/docs)
- [Supabase Documentation](https://supabase.com/docs)
- [Terraform Render Provider](https://registry.terraform.io/providers/render-oss/render/latest/docs)
- [Next.js Deployment](https://nextjs.org/docs/deployment)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)

---

## まとめ

このデプロイ計画に従うことで、MJAIアプリケーションを以下の構成で本番環境にデプロイできます：

- **データベース**: Supabase（既存プロジェクト使用）
- **バックエンド**: Render Web Service（Docker）
- **フロントエンド**: Render Web Service（Docker）
- **インフラ管理**: Terraform（オプション）

最小コストは月額$0（無料プラン）、推奨構成は月額$14（Starter プラン）です。
