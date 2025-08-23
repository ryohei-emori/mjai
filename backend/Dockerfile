# Stage 1: ビルドステージ
FROM python:3.11-slim AS builder

WORKDIR /app

# 依存関係のインストール
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: 本番ステージ
FROM python:3.11-slim AS production

# 作業ディレクトリの設定
WORKDIR /app

# 非rootユーザーの作成
RUN addgroup --system --gid 1001 fastapi && \
    adduser --system --uid 1001 --ingroup fastapi fastapi

# ヘルスチェック用パッケージのインストール
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# 依存関係をコピー (正しいパスを使用)
COPY --from=builder /root/.local /home/fastapi/.local

# 作業ディレクトリの所有権を変更
RUN chown fastapi:fastapi /app

# アプリケーションコードをコピー
COPY --chown=fastapi:fastapi . .

# PYTHONPATHとPATHを設定
ENV PYTHONPATH=/app
ENV PATH=/home/fastapi/.local/bin:$PATH

# 非rootユーザーに切り替え
USER fastapi

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# ポートの公開
EXPOSE 8000

# アプリケーションの起動
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] 