#!/bin/bash

set -e

echo "🚀 Starting MJAI development environment..."

# 1. ngrokだけ先に起動
echo "📦 Starting ngrok..."
docker-compose up -d ngrok

# 2. ngrokの準備を待つ
echo "⏳ Waiting for ngrok tunnels to be ready..."
sleep 8

# 3. ngrokのURLを取得して.envを自動更新
echo "🔄 Updating environment variables..."
./update-env.sh --no-docker

# 4. バックエンドを起動
echo "🔧 Starting backend..."
docker-compose up -d backend

# 5. フロントエンドを起動
echo "🌐 Starting frontend..."
docker-compose up -d frontend

echo "✅ Development environment is ready!"
echo ""
echo "📱 Frontend: http://localhost:3000"
echo "🔧 Backend API: http://localhost:8000"
echo "🌐 ngrok Dashboard: http://localhost:4040"
echo ""
echo "📋 To view logs: docker-compose logs -f"
echo "🛑 To stop: docker-compose down" 