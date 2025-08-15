#!/bin/bash

# ローカル環境でバックエンドを起動するスクリプト

# 現在のディレクトリを取得
CURRENT_DIR=$(pwd)

# 環境変数を設定
export PYTHONPATH="${CURRENT_DIR}"
export APP_ROOT="${CURRENT_DIR}"

echo "🚀 Starting backend in local mode..."
echo "PYTHONPATH: ${PYTHONPATH}"
echo "APP_ROOT: ${APP_ROOT}"

# 仮想環境が存在する場合はアクティベート
if [ -d "venv" ]; then
    echo "📦 Activating virtual environment..."
    source venv/bin/activate
fi

# 依存関係をインストール（必要に応じて）
if [ ! -f "venv" ]; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
fi

# バックエンドを起動
echo "🔧 Starting FastAPI backend..."
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 