#!/bin/bash

# ローカルからTerraformでデプロイするスクリプト

set -e

echo "=========================================="
echo "MJAI Terraform Deployment (Local)"
echo "=========================================="
echo ""

# カレントディレクトリの確認
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# terraform.tfvarsの存在確認
if [ ! -f "terraform.tfvars" ]; then
    echo "❌ Error: terraform.tfvars が見つかりません"
    echo ""
    echo "以下の手順で作成してください："
    echo "1. terraform.tfvars.example をコピー"
    echo "   cp terraform.tfvars.example terraform.tfvars"
    echo ""
    echo "2. terraform.tfvars を編集して実際の値を設定"
    echo "   - RENDER_API_KEY"
    echo "   - DATABASE_URL"
    echo "   - GEMINI_API_KEY"
    echo ""
    exit 1
fi

echo "✓ terraform.tfvars が見つかりました"
echo ""

# Terraformのバージョン確認
echo "Terraformバージョン確認..."
terraform version
echo ""

# Terraform初期化
echo "=========================================="
echo "Step 1: Terraform Init"
echo "=========================================="
terraform init
echo ""

# Terraform検証
echo "=========================================="
echo "Step 2: Terraform Validate"
echo "=========================================="
terraform validate
echo ""

# Terraformフォーマット確認
echo "=========================================="
echo "Step 3: Terraform Format Check"
echo "=========================================="
terraform fmt -check || {
    echo "⚠️  フォーマットの問題が見つかりました。自動修正します..."
    terraform fmt
    echo "✓ フォーマットを修正しました"
}
echo ""

# Terraformプラン
echo "=========================================="
echo "Step 4: Terraform Plan"
echo "=========================================="
terraform plan -out=tfplan
echo ""

# 確認プロンプト
echo "=========================================="
echo "デプロイ確認"
echo "=========================================="
echo "上記のプランを確認してください。"
echo ""
read -p "デプロイを実行しますか？ (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "❌ デプロイをキャンセルしました"
    rm -f tfplan
    exit 0
fi

# Terraform適用
echo ""
echo "=========================================="
echo "Step 5: Terraform Apply"
echo "=========================================="
terraform apply tfplan
echo ""

# プランファイルの削除
rm -f tfplan

# 出力の表示
echo ""
echo "=========================================="
echo "デプロイ完了！"
echo "=========================================="
terraform output
echo ""

echo "✓ デプロイが正常に完了しました"
echo ""
echo "次のステップ："
echo "1. バックエンドURL: https://mjai-backend.onrender.com/health"
echo "2. フロントエンドURL: https://mjai-frontend.onrender.com"
echo "3. Renderダッシュボードでデプロイ状況を確認"
echo ""
