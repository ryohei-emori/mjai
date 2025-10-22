# Terraform セットアップガイド

## Terraformのインストール

### macOS (Homebrew)

```bash
brew tap hashicorp/tap
brew install hashicorp/tap/terraform
```

### 確認

```bash
terraform version
# Terraform v1.5.0 以上が表示されればOK
```

## 初回セットアップ

### 1. terraform.tfvarsの作成

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

### 2. terraform.tfvarsの編集

以下の値を設定してください：

```hcl
# Render API Key
render_api_key = "rnd_xxxxxxxxxxxxxxxxxxxxx"

# Supabase Database URL
database_url = "postgresql://postgres.fqyhrubqkpuyliqojbai:YOUR_PASSWORD@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres"

# Gemini API
gemini_api_key = "AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
gemini_model   = "gemini-2.5-flash"
```

### 3. Terraform初期化

```bash
terraform init
```

### 4. プラン確認

```bash
terraform plan
```

### 5. デプロイ

```bash
# 簡単な方法（推奨）
./deploy-local.sh

# または手動で
terraform apply
```

## 必要な情報の取得方法

### Render API Key

1. [Render Dashboard](https://dashboard.render.com)にログイン
2. Account Settings → API Keys
3. "Create API Key"をクリック
4. キーをコピー

### Supabase Database URL

既に設定済みの`conf/.env`から取得：

```bash
grep DATABASE_URL conf/.env
```

### Gemini API Key

既に設定済みの`conf/.env`から取得：

```bash
grep GEMINI_API_KEY conf/.env
```

## トラブルシューティング

### Terraformがインストールできない

```bash
# Homebrewを更新
brew update

# 再度インストール
brew install hashicorp/tap/terraform
```

### terraform initが失敗する

```bash
# キャッシュをクリア
rm -rf .terraform .terraform.lock.hcl

# 再度初期化
terraform init
```

## 次のステップ

1. ローカルからデプロイ: `./deploy-local.sh`
2. GitHub Secretsを設定
3. mainブランチにpushして自動デプロイ

詳細は[デプロイガイド](./DEPLOY_GUIDE.md)を参照してください。
