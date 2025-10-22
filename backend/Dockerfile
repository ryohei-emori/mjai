FROM python:3.11-slim

# 作業ディレクトリの設定
WORKDIR /app

# 非rootユーザーの作成
RUN addgroup --system --gid 1001 fastapi && \
    adduser --system --uid 1001 --ingroup fastapi fastapi

# ヘルスチェック用パッケージのインストール
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# 依存関係をインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY --chown=fastapi:fastapi . .

# PYTHONPATHを設定
ENV PYTHONPATH=/app

# 非rootユーザーに切り替え
USER fastapi

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# ポートの公開
EXPOSE 8000

# アプリケーションの起動
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]