#!/bin/bash

set -e

echo "🚀 Starting MJAI development environment..."

# 1. すべてのサービスを停止・キャッシュ削除
echo "🛑 Stopping all containers and removing cache..."
docker-compose down --volumes --remove-orphans

echo "🧹 Removing old images (backend/frontend only)..."
docker rmi $(docker images --filter=reference='*backend*' --format '{{.ID}}') || true
docker rmi $(docker images --filter=reference='*frontend*' --format '{{.ID}}') || true

# 2. ngrokだけ先に起動
echo "📦 Starting ngrok..."
docker-compose up -d ngrok

# 3. ngrokの準備を待つ
echo "⏳ Waiting for ngrok tunnels to be ready..."
sleep 8

# 4. ngrokのURLを取得して.envを自動更新
echo "🔄 Updating environment variables..."
./update-env.sh --no-docker

# 5. バックエンド・フロントエンドのイメージをビルド
echo "🔧 Building backend and frontend images..."
docker-compose build backend frontend

# 6. バックエンドを起動
echo "🔧 Starting backend..."
docker-compose up -d backend

# 7. フロントエンドを起動
echo "🌐 Starting frontend..."
docker-compose up -d frontend

# ngrokのURLを表示
NGROK_BACKEND_URL=$(grep BACKEND_NGROK_URL ../conf/.env | cut -d'=' -f2)
NGROK_FRONTEND_URL=$(grep FRONTEND_NGROK_URL ../conf/.env | cut -d'=' -f2)
echo "🔗 ngrok Backend URL: $NGROK_BACKEND_URL"
echo "🔗 ngrok Frontend URL: $NGROK_FRONTEND_URL"

echo "✅ Development environment is ready!"
echo ""
echo "📱 Frontend: http://localhost:3000"
echo "🔧 Backend API: http://localhost:8000"
echo "🌐 ngrok Dashboard: http://localhost:4040"
echo ""
echo "📋 To view logs: docker-compose logs -f"
echo "🛑 To stop: docker-compose down"