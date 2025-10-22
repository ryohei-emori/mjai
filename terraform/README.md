# Terraform デプロイ設定

このディレクトリには、MJAIアプリケーションをRenderにデプロイするためのTerraform設定が含まれています。

## 構成

- **Backend**: Render Web Service (FastAPI + Docker)
- **Frontend**: Render Web Service (Next.js + Docker)
- **Database**: Supabase PostgreSQL (既存プロジェクト使用)

## 前提条件

1. **Terraformのインストール** (>= 1.5.0)
   ```bash
   brew install terraform
   ```

2. **Render APIキーの取得**
   - [Render Dashboard](https://dashboard.render.com) → Account Settings → API Keys

3. **Supabase接続情報**
   - DATABASE_URL（既に設定済み）

4. **Gemini APIキー**
   - Google Cloud Consoleから取得

## ローカルからのデプロイ

### 1. 設定ファイルの作成

```bash
# terraform.tfvars.example をコピー
cp terraform.tfvars.example terraform.tfvars

# terraform.tfvars を編集して実際の値を設定
vim terraform.tfvars
```

必要な変数：
- `render_api_key`: RenderのAPIキー
- `database_url`: Supabaseの接続URL
- `gemini_api_key`: Gemini APIキー
- `gemini_model`: 使用するモデル（デフォルト: gemini-2.5-flash）

### 2. デプロイスクリプトの実行

```bash
# デプロイスクリプトを実行
./deploy-local.sh
```

このスクリプトは以下を実行します：
1. Terraform初期化
2. 設定の検証
3. プランの作成と確認
4. デプロイの実行
5. 結果の表示

### 3. 手動実行（詳細制御が必要な場合）

```bash
# 初期化
terraform init

# フォーマット確認
terraform fmt -check

# 検証
terraform validate

# プラン作成
terraform plan -out=tfplan

# 適用
terraform apply tfplan

# 出力確認
terraform output
```

## GitHub Actionsからの自動デプロイ

mainブランチへのpush時に自動的にデプロイされます。

### 必要なGitHub Secrets

以下のシークレットをGitHubリポジトリに設定してください：

| シークレット名 | 説明 |
|--------------|------|
| `RENDER_API_KEY` | RenderのAPIキー |
| `DATABASE_URL` | Supabaseの接続URL |
| `GEMINI_API_KEY` | Gemini APIキー |
| `GEMINI_MODEL` | 使用するGeminiモデル |

設定方法：
1. GitHub → Settings → Secrets and variables → Actions
2. "New repository secret"をクリック
3. 各シークレットを追加

### ワークフローのトリガー

**自動トリガー**:
- mainブランチへのpush
- backend/、frontend/、terraform/ディレクトリの変更時

**手動トリガー**:
```bash
# GitHub Actions → Deploy to Render → Run workflow
```

## デプロイ後の確認

### ヘルスチェック

```bash
# バックエンド
curl https://mjai-backend.onrender.com/health

# フロントエンド
curl https://mjai-frontend.onrender.com
```

### ログ確認

```bash
# Terraform出力の確認
terraform output

# Renderダッシュボードでログを確認
# https://dashboard.render.com
```

## トラブルシューティング

### Terraform初期化エラー

```bash
# キャッシュをクリア
rm -rf .terraform .terraform.lock.hcl
terraform init
```

### プロバイダーのバージョンエラー

```bash
# プロバイダーを更新
terraform init -upgrade
```

### 環境変数が反映されない

```bash
# terraform.tfvarsの内容を確認
cat terraform.tfvars

# 環境変数を直接指定
terraform plan \
  -var="render_api_key=YOUR_KEY" \
  -var="database_url=YOUR_URL"
```

### デプロイが失敗する

1. Renderダッシュボードでサービスのログを確認
2. GitHub Actionsのログを確認
3. terraform planで変更内容を確認

## リソースの削除

```bash
# すべてのリソースを削除
terraform destroy

# 確認プロンプトで "yes" を入力
```

**注意**: この操作はRender上のサービスを削除します。Supabaseのデータベースは削除されません。

## ファイル構成

```
terraform/
├── main.tf                    # メインの設定ファイル
├── variables.tf               # 変数定義
├── outputs.tf                 # 出力定義
├── terraform.tfvars.example   # 設定例
├── terraform.tfvars           # 実際の設定（Git管理外）
├── deploy-local.sh            # ローカルデプロイスクリプト
└── README.md                  # このファイル
```

## 参考リンク

- [Terraform Documentation](https://www.terraform.io/docs)
- [Render Terraform Provider](https://registry.terraform.io/providers/render-oss/render/latest/docs)
- [Render Documentation](https://render.com/docs)

## サポート

問題が発生した場合は、以下を確認してください：

1. Terraformのバージョン（>= 1.5.0）
2. Render APIキーの有効性
3. GitHub Secretsの設定
4. Renderダッシュボードのサービス状態
