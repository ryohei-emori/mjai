#!/bin/bash
# Supabase(PostgreSQL)接続テストスクリプト
# .envのDATABASE_URLを使ってpsql疎通・SQL実行・SSL確認を行う

set -e

# .envからDATABASE_URLを取得
env_path="$(dirname "$0")/.env"
db_url=$(grep '^DATABASE_URL=' "$env_path" | cut -d '=' -f2-)

if [ -z "$db_url" ]; then
  echo "DATABASE_URL not found in $env_path"
  exit 1
fi

echo "[INFO] DATABASE_URL: $db_url"

# psqlコマンドがあるか確認
type psql >/dev/null 2>&1 || { echo >&2 "psql is not installed. Please install postgresql-client."; exit 1; }

# 1. 接続テスト（バージョン表示）
echo "[INFO] Try connecting to Supabase with psql..."
psql "$db_url" -c 'SELECT version();' --set=sslmode=require

# 2. テーブル一覧表示
echo "[INFO] List tables in public schema..."
psql "$db_url" -c "\dt public.*" --set=sslmode=require

# 3. サンプルクエリ（セッション数カウント）
echo "[INFO] Count sessions..."
psql "$db_url" -c "SELECT COUNT(*) FROM sessions;" --set=sslmode=require

echo "[SUCCESS] Supabase(PostgreSQL) connection and basic queries succeeded."
