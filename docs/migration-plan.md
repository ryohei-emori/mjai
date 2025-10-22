# SQLite → Supabase マイグレーション手順

## 概要

このドキュメントでは、ローカルのSQLiteデータベース（`app.db`）をSupabase（PostgreSQL）に高速で移行する方法を説明します。

## 方法の選択

### ❌ 直接Supabaseに挿入（遅い）
- 各レコードを1つずつSupabaseに挿入
- ネットワーク遅延により非常に時間がかかる
- 2000件以上のレコードで数分〜数十分かかる

### ✅ ローカルPostgreSQL経由（高速）
- ローカルでSQLite → PostgreSQLに変換（0.1秒）
- ダンプファイルを作成
- ダンプをSupabaseに一括アップロード（数秒）
- **合計時間: 数秒〜数十秒**

## 前提条件

1. PostgreSQLがインストールされていること
   ```bash
   brew install postgresql@14
   ```

2. 必要なPythonパッケージがインストールされていること
   ```bash
   pip install asyncpg python-dotenv
   ```

3. `.env`ファイルにSupabase接続情報が設定されていること
   ```
   DATABASE_URL=postgresql://postgres.PROJECT_REF:PASSWORD@aws-0-REGION.pooler.supabase.com:6543/postgres
   ```

## マイグレーション手順

### ステップ1: ローカルPostgreSQLサーバーを起動

```bash
brew services start postgresql@14
```

起動確認:
```bash
pg_isready
# /tmp:5432 - accepting connections
```

### ステップ2: 一時データベースを作成

```bash
createdb mjai_temp
```

### ステップ3: SQLiteからローカルPostgreSQLに移行

```bash
python3 backend/db/migrate_local.py
```

**出力例:**
```
Starting migration from SQLite to Local PostgreSQL...
Counting records...
Found 24 sessions, 291 histories, 2018 proposals
Total records to migrate: 2333
==================================================

Creating tables...
✓ Tables created

Migrating sessions...
✓ Migrated 24 sessions in 0.0s

Migrating correction histories...
✓ Migrated 290 histories in 0.0s

Migrating AI proposals...
✓ Batch 1/3: 1000 proposals in 0.0s
✓ Batch 2/3: 1000 proposals in 0.0s
✓ Batch 3/3: 18 proposals in 0.0s

==================================================
✓ Migration to local PostgreSQL completed!
  Total time: 0.1s
  Total records migrated: 2332
==================================================
```

### ステップ4: ダンプファイルを作成

```bash
pg_dump mjai_temp --no-owner --no-acl > /tmp/mjai_dump.sql
```

### ステップ5: Supabaseの既存データをクリア

```bash
PGPASSWORD='YOUR_PASSWORD' psql \
  -h aws-0-REGION.pooler.supabase.com \
  -p 6543 \
  -U postgres.PROJECT_REF \
  -d postgres \
  -c "DROP TABLE IF EXISTS ai_proposals CASCADE; 
      DROP TABLE IF EXISTS correction_histories CASCADE; 
      DROP TABLE IF EXISTS sessions CASCADE;"
```

### ステップ6: ダンプをSupabaseにリストア

```bash
PGPASSWORD='YOUR_PASSWORD' psql \
  -h aws-0-REGION.pooler.supabase.com \
  -p 6543 \
  -U postgres.PROJECT_REF \
  -d postgres \
  < /tmp/mjai_dump.sql
```

### ステップ7: データを確認

```bash
PGPASSWORD='YOUR_PASSWORD' psql \
  -h aws-0-REGION.pooler.supabase.com \
  -p 6543 \
  -U postgres.PROJECT_REF \
  -d postgres \
  -c "SELECT 'sessions' as table_name, COUNT(*) as count FROM public.sessions 
      UNION ALL 
      SELECT 'correction_histories', COUNT(*) FROM public.correction_histories 
      UNION ALL 
      SELECT 'ai_proposals', COUNT(*) FROM public.ai_proposals;"
```

**期待される出力:**
```
      table_name      | count 
----------------------+-------
 sessions             |    24
 correction_histories |   290
 ai_proposals         |  2018
(3 rows)
```

### ステップ8: クリーンアップ

```bash
# PostgreSQLサーバーを停止
brew services stop postgresql@14

# 一時データベースを削除
dropdb mjai_temp

# ダンプファイルを削除
rm /tmp/mjai_dump.sql
```

## ワンライナー実行

全ステップを一度に実行する場合:

```bash
# 1. PostgreSQL起動とDB作成
brew services start postgresql@14 && \
sleep 3 && \
createdb mjai_temp && \

# 2. ローカルに移行
python3 backend/db/migrate_local.py && \

# 3. ダンプ作成
pg_dump mjai_temp --no-owner --no-acl > /tmp/mjai_dump.sql && \

# 4. Supabaseをクリアしてリストア
PGPASSWORD='YOUR_PASSWORD' psql \
  -h aws-0-REGION.pooler.supabase.com \
  -p 6543 \
  -U postgres.PROJECT_REF \
  -d postgres \
  -c "DROP TABLE IF EXISTS ai_proposals CASCADE; 
      DROP TABLE IF EXISTS correction_histories CASCADE; 
      DROP TABLE IF EXISTS sessions CASCADE;" && \

PGPASSWORD='YOUR_PASSWORD' psql \
  -h aws-0-REGION.pooler.supabase.com \
  -p 6543 \
  -U postgres.PROJECT_REF \
  -d postgres \
  < /tmp/mjai_dump.sql && \

# 5. クリーンアップ
brew services stop postgresql@14 && \
dropdb mjai_temp && \
rm /tmp/mjai_dump.sql && \

echo "✓ Migration completed successfully!"
```

## トラブルシューティング

### PostgreSQLが起動しない

```bash
# ログを確認
brew services list
brew services restart postgresql@14
```

### 接続エラー

```bash
# DNS解決を確認
nslookup aws-0-REGION.pooler.supabase.com

# 接続テスト
PGPASSWORD='YOUR_PASSWORD' psql \
  -h aws-0-REGION.pooler.supabase.com \
  -p 6543 \
  -U postgres.PROJECT_REF \
  -d postgres \
  -c "SELECT version();"
```

### 無効なUUIDエラー

`migrate_local.py`スクリプトは自動的に無効なUUIDを持つレコードをスキップまたは新しいUUIDを生成します。Warningが表示されますが、マイグレーションは続行されます。

### テーブルが既に存在するエラー

ステップ5を実行して既存のテーブルを削除してから、再度ステップ6を実行してください。

## パフォーマンス比較

| 方法 | 2332レコードの移行時間 |
|------|----------------------|
| 直接Supabase挿入 | 数分〜数十分 |
| ローカルPostgreSQL経由 | **数秒〜数十秒** |

## スクリプトファイル

- `backend/db/migrate_local.py` - SQLiteからローカルPostgreSQLへの移行スクリプト
- `backend/db/migrate_to_supabase.py` - 直接Supabaseに挿入する旧スクリプト（非推奨）

## 注意事項

1. マイグレーション前に必ずデータのバックアップを取ってください
2. 本番環境での実行前にテスト環境で動作確認してください
3. Supabaseの接続情報（パスワード等）は`.env`ファイルで管理し、Gitにコミットしないでください
4. 大量データの場合、ダンプファイルのサイズに注意してください
