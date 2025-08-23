#!/bin/zsh
# MJAIデプロイ用一括シェルスクリプト
# fly.io(frontend), Render(backend), Supabase(DB)のデプロイ/セットアップ用

set -e

# 1. Supabase: スキーマ投入 (手動でSQL Editor推奨)
echo "[1] Supabase SQLスキーマ投入: conf/supabase/migrations/001_initial_schema.sql をSupabase SQL Editorで実行してください"

# 2. Python仮想環境の作成・依存インストール (推奨: 3.11)
echo "[2] Python仮想環境セットアップ (backend)"
cd ../backend
if [ ! -d "venv" ]; then
  python3.11 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cd ../conf

echo "[3] conf/.envの値を最新化し、各サービスの管理画面で環境変数を設定してください"
echo "   - conf/.env, conf/.env.example を参考に、Supabase/Render/fly.ioのWeb管理画面で値をセット"

echo "[4] Render: GitHub mainブランチ連携・デプロイ (Web管理画面で操作)"
echo "   - https://dashboard.render.com/ でWeb Service作成・mainブランチを選択"
echo "   - 環境変数(DATABASE_URL, GEMINI_API_KEY, FRONTEND_URL等)を設定"

echo "[5] fly.io: GitHub mainブランチ連携・デプロイ (Web管理画面で操作)"
echo "   - https://fly.io/dashboard で新規アプリ作成・mainブランチを選択"
echo "   - 環境変数(NEXT_PUBLIC_SUPABASE_URL等)を設定"

echo "[6] 動作確認: フロントエンドURL/バックエンドAPI/DB接続を確認"
echo "   - fly.ioのURLにアクセスし、アプリが動作するか確認"
echo "   - RenderのAPIエンドポイントも直接テスト"

echo "--- 完了！ ---"
