# MJAI デプロイ手順書 (Render)

このドキュメントでは、MJAIアプリケーションをRenderにデプロイする手順を説明します。
フロントエンド、バックエンド、データベースすべてをRenderで管理し、Terraformを使用してインフラを構成します。

## デプロイ構成

- **フロントエンド**: Render Web Service (Next.js)
- **バックエンド**: Render Web Service (FastAPI)
- **データベース**: Render Managed PostgreSQL

## 前提条件

- GitHubアカウント
- Renderアカウント
- Terraformインストール済み
- 環境変数管理の理解

## 1. データベースの移行 (SQLite → Supabase)

### 1.1 Supabaseプロジェクトの作成

1. [Supabase](https://supabase.com)にアクセスしてアカウントを作成
2. 新しいプロジェクトを作成
3. プロジェクトの設定から以下を取得：
   - Project URL
   - Project API Key (anon, public)
   - Database Password

### 1.2 データベーススキーマの移行

現在のSQLiteスキーマをSupabaseに移行します。

```sql
-- Supabase SQL Editorで実行

-- Sessionsテーブル
CREATE TABLE sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    name TEXT,
    correction_count INTEGER DEFAULT 0,
    is_open BOOLEAN DEFAULT true
);

-- CorrectionHistoriesテーブル
CREATE TABLE correction_histories (
    history_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(session_id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    original_text TEXT NOT NULL,
    instruction_prompt TEXT,
    target_text TEXT,
    combined_comment TEXT,
    selected_proposal_ids TEXT,
    custom_proposals TEXT
);

-- AIProposalsテーブル
CREATE TABLE ai_proposals (
    proposal_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    history_id UUID REFERENCES correction_histories(history_id) ON DELETE CASCADE,
    proposal_text TEXT NOT NULL,
    confidence_score REAL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- インデックスの作成
CREATE INDEX idx_sessions_updated_at ON sessions(updated_at DESC);
CREATE INDEX idx_histories_session_id ON correction_histories(session_id);
CREATE INDEX idx_histories_timestamp ON correction_histories(timestamp DESC);
CREATE INDEX idx_proposals_history_id ON ai_proposals(history_id);

-- RLS (Row Level Security) の有効化
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE correction_histories ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_proposals ENABLE ROW LEVEL SECURITY;

-- 基本的なポリシー（必要に応じて調整）
CREATE POLICY "Allow all operations for authenticated users" ON sessions FOR ALL USING (true);
CREATE POLICY "Allow all operations for authenticated users" ON correction_histories FOR ALL USING (true);
CREATE POLICY "Allow all operations for authenticated users" ON ai_proposals FOR ALL USING (true);
```

### 1.3 データベース接続設定

`backend/requirements.txt`に以下を追加：

```txt
psycopg2-binary==2.9.9
asyncpg==0.29.0
```

## 2. バックエンドの修正 (FastAPI + Supabase)

### 2.1 データベースヘルパーの更新

`backend/app/db_helper.py`を以下のように更新：

```python
import os
import asyncpg
from typing import List, Dict, Optional
from contextlib import asynccontextmanager

# Supabase接続設定
DATABASE_URL = os.environ.get("DATABASE_URL")

@asynccontextmanager
async def get_db():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        yield conn
    finally:
        await conn.close()

# セッション一覧取得
async def fetch_sessions():
    async with get_db() as conn:
        rows = await conn.fetch(
            'SELECT * FROM sessions ORDER BY updated_at DESC'
        )
        return [dict(row) for row in rows]

# セッション追加
async def insert_session(session):
    async with get_db() as conn:
        await conn.execute(
            '''
            INSERT INTO sessions (session_id, created_at, updated_at, name, correction_count, is_open) 
            VALUES ($1, $2, $3, $4, $5, $6)
            ''',
            session['session_id'],
            session['created_at'],
            session['updated_at'],
            session.get('name'),
            session.get('correction_count', 0),
            session.get('is_open', True)
        )

# その他の関数も同様にasync/awaitパターンに変更
```

### 2.2 環境変数の設定

`backend/.env`ファイルを作成：

```env
# Supabase設定
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@[YOUR-PROJECT-REF].supabase.co:5432/postgres

# Gemini API
GEMINI_API_KEY=[YOUR-GEMINI-API-KEY]

# 環境設定
ENVIRONMENT=production
FRONTEND_URL=https://[YOUR-FLOW-APP].fly.io
```

### 2.3 CORS設定の更新

`backend/app/main.py`のCORS設定を更新：

```python
# 本番環境用のCORS設定
if os.environ.get("ENVIRONMENT", "development") == "production":
    cors_origins = [
        os.environ.get("FRONTEND_URL"),
        "https://*.fly.io"
    ]
else:
    cors_origins = get_cors_origins()
```

## 3. フロントエンドの修正 (Next.js + Supabase)

### 3.1 環境変数の設定

`frontend/.env.local`ファイルを作成：

```env
# Supabase設定
NEXT_PUBLIC_SUPABASE_URL=https://[YOUR-PROJECT-REF].supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=[YOUR-ANON-KEY]

# バックエンドAPI
NEXT_PUBLIC_API_URL=https://[YOUR-RENDER-APP].onrender.com

# Gemini API
NEXT_PUBLIC_GEMINI_API_KEY=[YOUR-GEMINI-API-KEY]
```

### 3.2 APIクライアントの更新

`frontend/src/app/api.ts`を更新してSupabaseを使用：

```typescript
import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

export const supabase = createClient(supabaseUrl, supabaseAnonKey)

// API関数の更新例
export async function fetchSessions() {
  const { data, error } = await supabase
    .from('sessions')
    .select('*')
    .order('updated_at', { ascending: false })
  
  if (error) throw error
  return data
}
```

### 3.3 依存関係の追加

`frontend/package.json`に以下を追加：

```json
{
  "dependencies": {
    "@supabase/supabase-js": "^2.39.0"
  }
}
```

## 4. Renderへのバックエンドデプロイ

### 4.1 Renderプロジェクトの作成

1. [Render](https://render.com)にアクセスしてアカウントを作成
2. "New +" → "Web Service" を選択
3. GitHubリポジトリを接続

### 4.2 サービス設定

以下の設定でWebサービスを作成：

- **Name**: `mjai-backend`
- **Environment**: `Python 3`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Plan**: Free（または必要に応じて有料プラン）

### 4.3 環境変数の設定

Renderのダッシュボードで以下の環境変数を設定：

```
DATABASE_URL=postgresql://postgres:[PASSWORD]@[PROJECT-REF].supabase.co:5432/postgres
GEMINI_API_KEY=[YOUR-GEMINI-API-KEY]
ENVIRONMENT=production
FRONTEND_URL=https://[YOUR-FLOW-APP].fly.io
```

### 4.4 デプロイ設定ファイル

`backend/render.yaml`を作成：

```yaml
services:
  - type: web
    name: mjai-backend
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: DATABASE_URL
        sync: false
      - key: GEMINI_API_KEY
        sync: false
      - key: ENVIRONMENT
        value: production
      - key: FRONTEND_URL
        sync: false
```

## 5. fly.ioへのフロントエンドデプロイ

### 5.1 fly.ioプロジェクトの作成

1. [fly.io](https://fly.io)にアクセスしてアカウントを作成
2. "New Project" → "Import from Git" を選択
3. GitHubリポジトリを接続

### 5.2 ビルド設定

以下の設定でプロジェクトを設定：

- **Framework Preset**: `Next.js`
- **Build Command**: `npm run build`
- **Output Directory**: `.next`
- **Install Command**: `npm install`

### 5.3 環境変数の設定

fly.ioのダッシュボードで以下の環境変数を設定：

```
NEXT_PUBLIC_SUPABASE_URL=https://[YOUR-PROJECT-REF].supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=[YOUR-ANON-KEY]
NEXT_PUBLIC_API_URL=https://[YOUR-RENDER-APP].onrender.com
NEXT_PUBLIC_GEMINI_API_KEY=[YOUR-GEMINI-API-KEY]
```

### 5.4 カスタムドメインの設定（オプション）

1. fly.ioのダッシュボードで "Settings" → "Domains" に移動
2. カスタムドメインを追加
3. DNSレコードを設定

## 6. デプロイ後の確認とテスト

### 6.1 基本的な動作確認

1. フロントエンドアプリケーションにアクセス
2. バックエンドAPIのエンドポイントをテスト
3. データベース接続を確認

### 6.2 ログの確認

- **Render**: ダッシュボードの "Logs" タブ
- **fly.io**: ダッシュボードの "Deployments" → "View Logs"

### 6.3 パフォーマンステスト

- ページ読み込み速度
- APIレスポンス時間
- データベースクエリの実行時間

## 7. 本番環境での注意事項

### 7.1 セキュリティ

- 環境変数は必ず暗号化して管理
- APIキーは定期的にローテーション
- CORS設定は必要最小限に制限

### 7.2 監視とアラート

- アプリケーションの可用性監視
- エラーレートの監視
- パフォーマンスメトリクスの監視

### 7.3 バックアップ

- Supabaseの自動バックアップ設定
- 重要なデータの定期エクスポート

## 8. トラブルシューティング

### 8.1 よくある問題

**データベース接続エラー**
- DATABASE_URLの形式確認
- Supabaseのファイアウォール設定確認

**CORSエラー**
- フロントエンドURLの設定確認
- バックエンドのCORS設定確認

**ビルドエラー**
- 依存関係のバージョン確認
- Node.js/Pythonのバージョン確認

### 8.2 ログの確認方法

各サービスのログを確認して問題を特定：

```bash
# Render
# ダッシュボードのLogsタブで確認

# fly.io
# ダッシュボードのDeploymentsで確認
```

## 9. コスト最適化

### 9.1 無料プランの制限

- **Render**: 月間750時間（無料）
- **fly.io**: 月間100GB転送（無料）
- **Supabase**: 月間500MB、2プロジェクト（無料）

### 9.2 有料プランへの移行

必要に応じて有料プランに移行：

- **Render**: $7/月から
- **fly.io**: $20/月から
- **Supabase**: $25/月から

## 10. 今後の拡張性

### 10.1 スケーリング

- ロードバランサーの追加
- CDNの導入
- データベースのレプリケーション

### 10.2 機能追加

- ユーザー認証システム
- リアルタイム通知
- 分析ダッシュボード

---

## まとめ

この手順書に従って、MJAIアプリケーションをfly.io、Render、Supabaseにデプロイすることで、常時アクセス可能なWebアプリケーションを構築できます。

各ステップで問題が発生した場合は、各サービスのドキュメントを参照するか、ログを確認してトラブルシューティングを行ってください。

デプロイが完了したら、定期的なメンテナンスと監視を行い、アプリケーションの安定性を確保してください。

---

## 付録: SQLite から Supabase(PostgreSQL) への完全移行手順

この付録は、開発時の SQLite ベース実装から、本番運用を想定した Supabase（PostgreSQL）へ「バックエンドの永続化」と「フロントエンドからの利用」を完全移行するための手順をまとめたものです。既存の API 仕様を変えずに移行する方針です。

### A. 必要情報の取得（Supabase Dashboard）
- Project URL（例: https://xxxx.supabase.co）
- anon public key（クライアント公開用）
- Database 接続文字列（Postgres）
  - 例: `postgresql://postgres:<PASSWORD>@db.<project-ref>.supabase.co:6543/postgres?sslmode=require`

### B. 環境変数の統一管理（conf/.env）
以下を conf/.env に設定（すでに運用している場合は上書き）

```env
# Backend → Supabase(Postgres)
DATABASE_URL=postgresql://postgres:<PASSWORD>@db.<project-ref>.supabase.co:6543/postgres?sslmode=require

# Frontend（現状: 直接DBは触らずAPI経由。将来SSR等でSupabase SDKを使うなら必須）
NEXT_PUBLIC_SUPABASE_URL=https://<project-ref>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon-public-key>

# API 経由アクセス
NEXT_PUBLIC_API_BASE_URL=https://<your-backend-ngrok-or-prod-url>
```

メモ: `sslmode=require` を必ず付与（asyncpg は SSL を要求）。

### C. Supabase スキーマ（アプリ互換）
既存アプリ（フロント/バック）で扱うフィールド名を維持したまま PG へ移すため、SQLite に近い構造でスキーマを定義します（型は PG 向けに最適化）。Supabase の SQL Editor で実行してください。

```sql
-- sessions
create table if not exists sessions (
  session_id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  name text,
  correction_count integer not null default 0,
  is_open boolean not null default true
);

-- correction_histories
create table if not exists correction_histories (
  history_id uuid primary key default gen_random_uuid(),
  session_id uuid not null references sessions(session_id) on delete cascade,
  timestamp timestamptz not null default now(),
  original_text text not null,
  instruction_prompt text,
  target_text text not null,
  combined_comment text,
  selected_proposal_ids text,
  custom_proposals text
);

-- ai_proposals（アプリの要求に合わせたカラム構成）
create table if not exists ai_proposals (
  proposal_id uuid primary key default gen_random_uuid(),
  history_id uuid not null references correction_histories(history_id) on delete cascade,
  type text not null, -- 'AI' | 'Custom'
  original_after_text text not null,
  original_reason text,
  modified_after_text text,
  modified_reason text,
  is_selected boolean not null default false,
  is_modified boolean not null default false,
  is_custom boolean not null default false,
  selected_order integer,
  created_at timestamptz not null default now()
);

-- index
create index if not exists idx_histories_session_id on correction_histories(session_id);
create index if not exists idx_histories_timestamp on correction_histories(timestamp desc);
create index if not exists idx_proposals_history_id on ai_proposals(history_id);

-- RLS（必要なら適宜絞る）
alter table sessions enable row level security;
alter table correction_histories enable row level security;
alter table ai_proposals enable row level security;
create policy "all for anon" on sessions for all using (true);
create policy "all for anon" on correction_histories for all using (true);
create policy "all for anon" on ai_proposals for all using (true);
```

既存の `backend/supabase/migrations/001_initial_schema.sql` は簡略化された列構成（`proposal_text` 等）で、現行アプリの API とは差異があります。上の「アプリ互換スキーマ」を使うとコード変更が最小です。

### D. バックエンドを PostgreSQL 経由に切り替える

現状 `backend/app/main.py` は SQLite 用関数を使用しています。以下の置換で asyncpg 経由の関数に切り替えます（関数名はすでに `db_helper.py` に実装済み）。

対象ファイル: `backend/app/main.py`

1) sessions 系
```diff
- return fetch_sessions_sqlite()
+ return await fetch_sessions()

- insert_session_sqlite(session)
+ await insert_session(session)

- return fetch_session_sqlite(session_id)
+ return await db_fetch_session(session_id)

- delete_session_sqlite(session_id)
+ await db_delete_session(session_id)

- update_session_sqlite(session_id, payload)
+ await db_update_session(session_id, payload)
```

2) histories 系
```diff
- return fetch_histories_by_session_sqlite(session_id)
+ return await fetch_histories_by_session(session_id)

- insert_history_sqlite(history)
+ await insert_history(history)
```

3) proposals 系
```diff
- return fetch_proposals_by_history_sqlite(history_id)
+ return await fetch_proposals_by_history(history_id)

- insert_proposal_sqlite(proposal)
+ await insert_proposal(proposal)
```

4) 関数シグネチャは async に合わせて `async def` に変更し、FastAPI が await する形へ（上記 diff 参照）。

5) `DATABASE_URL` を conf/.env → backend 実行環境に反映する（Render 等の環境変数にも設定）。

注意: `db_helper.py` の PostgreSQL 側実装は上記「アプリ互換スキーマ」を前提に以下のクエリに調整してください（概略）。

```sql
-- sessions
select * from sessions order by updated_at desc;
insert into sessions(session_id, created_at, updated_at, name, correction_count, is_open)
values($1, $2, $3, $4, $5, $6);

-- correction_histories
select * from correction_histories where session_id = $1 order by timestamp desc;
insert into correction_histories(...columns...) values($1, ...);

-- ai_proposals（payload をそのまま保存）
insert into ai_proposals (
  proposal_id, history_id, type, original_after_text, original_reason,
  modified_after_text, modified_reason, is_selected, is_modified, is_custom, selected_order
) values ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11);
```

### E. 既存データの移行（任意）
ローカルの SQLite（`backend/db/app.db`）から Supabase(Postgres) に移行するためのワンショットスクリプト例（ローカル実行）：

```python
# migrate_sqlite_to_supabase.py
import os, sqlite3, asyncio, asyncpg

DATABASE_URL = os.environ["DATABASE_URL"]
SQLITE_PATH = os.path.join(os.path.dirname(__file__), "backend", "db", "app.db")

async def main():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        sq = sqlite3.connect(SQLITE_PATH)
        sq.row_factory = sqlite3.Row

        # sessions
        for row in sq.execute("select * from Sessions"):
            await conn.execute(
                """
                insert into sessions(session_id, created_at, updated_at, name, correction_count, is_open)
                values($1,$2,$3,$4,$5,$6)
                on conflict (session_id) do nothing
                """,
                row["sessionId"], row["createdAt"], row["updatedAt"], row["name"], row["correctionCount"], bool(row["isOpen"]) 
            )

        # histories
        for row in sq.execute("select * from CorrectionHistories"):
            await conn.execute(
                """
                insert into correction_histories(
                  history_id, session_id, timestamp, original_text, instruction_prompt,
                  target_text, combined_comment, selected_proposal_ids, custom_proposals
                ) values($1,$2,$3,$4,$5,$6,$7,$8,$9)
                on conflict (history_id) do nothing
                """,
                row["historyId"], row["sessionId"], row["timestamp"], row["originalText"], row["instructionPrompt"],
                row["targetText"], row["combinedComment"], row["selectedProposalIds"], row["customProposals"],
            )

        # proposals
        for row in sq.execute("select * from AIProposals"):
            await conn.execute(
                """
                insert into ai_proposals(
                  proposal_id, history_id, type, original_after_text, original_reason,
                  modified_after_text, modified_reason, is_selected, is_modified, is_custom, selected_order
                ) values($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
                on conflict (proposal_id) do nothing
                """,
                row["proposalId"], row["historyId"], row["type"], row["originalAfterText"], row.get("originalReason"),
                row.get("modifiedAfterText"), row.get("modifiedReason"), bool(row["isSelected"]), bool(row["isModified"]), bool(row.get("isCustom") or 0), row.get("selectedOrder")
            )

        sq.close()
    finally:
        await conn.close()

asyncio.run(main())
```

実行例:

```bash
export DATABASE_URL=postgresql://postgres:<PASSWORD>@db.<project-ref>.supabase.co:6543/postgres?sslmode=require
python migrate_sqlite_to_supabase.py
```

### F. デプロイ/運用設定

- Render（Backend）: `DATABASE_URL`, `ENVIRONMENT=production`, `FRONTEND_URL` を設定し再デプロイ
- fly.io（Frontend）: `NEXT_PUBLIC_API_BASE_URL` をバックエンドの公開URLに、Supabase の `NEXT_PUBLIC_*` を設定
- CORS: バックエンドの CORS 設定にフロントの本番 URL を追加

### G. 動作検証チェックリスト

- `GET /sessions` が 200 でセッション一覧を返す
- セッション作成→履歴保存→提案作成が一連で成功し、Supabase の該当テーブルにレコードが増える
- フロント UI から同等の操作が成功する

以上で、SQLite から Supabase(PostgreSQL) への完全移行が完了します。