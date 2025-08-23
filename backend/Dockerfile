FROM python:3.11-slim AS builder

WORKDIR /app

# 依存関係のインストール
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim AS production

WORKDIR /app

# ヘルスチェック用パッケージのインストール
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# 非rootユーザーの作成
RUN addgroup --system --gid 1001 fastapi && \
    adduser --system --uid 1001 --ingroup fastapi fastapi

# 依存関係をコピー
COPY --from=builder /root/.local /home/fastapi/.local

# アプリケーションコードのコピー
COPY --chown=fastapi:fastapi . .

# PYTHONPATHを設定
ENV PYTHONPATH=/app
ENV PATH=/home/fastapi/.local/bin:$PATH

# 非rootユーザーに切り替え
USER fastapi

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# ポートの公開
EXPOSE 8000

# アプリケーションの起動（本番環境では--reloadを削除）
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] 