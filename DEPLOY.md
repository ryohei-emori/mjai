# MJAI Webアプリケーション デプロイ手順書

このドキュメントでは、MJAIアプリケーションを以下のサービスにデプロイして、常時アクセス可能なWebアプリケーションにする手順を説明します。

## デプロイ構成

- **フロントエンド**: [Fly.io](https://fly.io) (Vercel代替)
- **バックエンド**: [Render](https://render.com)
- **データベース**: [Supabase](https://supabase.com)

## 前提条件

- GitHubアカウント
- Supabaseアカウント
- Renderアカウント
- fly.ioアカウント
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