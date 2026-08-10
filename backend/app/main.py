import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from uuid import uuid4
from pathlib import Path
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# 環境変数からアプリケーションルートを取得
app_root = os.environ.get("APP_ROOT", "/app")

# .env の探索候補
_env_candidates = [
    os.path.join(app_root, "..", "conf", ".env"),  # /conf/.env を想定
    os.path.join(app_root, ".env"),                   # /app/.env マウント
    "/conf/.env",                                     # 直接マウント
]
for _path in _env_candidates:
    if os.path.exists(_path):
        load_dotenv(dotenv_path=_path, override=False)
        break

from .db_helper import (
    fetch_sessions, insert_session, 
    delete_session as db_delete_session, 
    update_session as db_update_session, 
    fetch_session as db_fetch_session,
    fetch_histories_by_session, insert_history,
    fetch_proposals_by_history, insert_proposal,
)
from uuid import uuid4
from datetime import datetime
from fastapi import APIRouter
from fastapi import Body, Depends

from .auth import get_current_user

# CORS設定 - 環境変数から自動取得
def get_cors_origins():
    # 基本のローカル開発用オリジン
    cors_origins = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:8080",
        "http://192.168.0.34:3000",
        "http://192.168.0.34:3001",
        "http://172.22.178.95:3000",
        "http://172.22.178.95:3001",
        "http://0.0.0.0:3000",
        "http://0.0.0.0:3001",
        "http://0.0.0.0:8080",
    ]
    
    print("=== Backend CORS Debug ===")
    print("Environment variables:")
    print(f"FRONTEND_URL: {os.environ.get('FRONTEND_URL')}")
    print(f"FRONTEND_NGROK_URL: {os.environ.get('FRONTEND_NGROK_URL')}")
    print(f"BACKEND_NGROK_URL: {os.environ.get('BACKEND_NGROK_URL')}")
    
    # Vercel/本番フロントエンドURL (FRONTEND_URL env var)
    frontend_url = os.environ.get("FRONTEND_URL")
    if frontend_url:
        cors_origins.append(frontend_url)
        print(f"Added frontend URL to CORS: {frontend_url}")
    
    # 環境変数からngrok URLを取得して追加
    frontend_ngrok_url = os.environ.get("FRONTEND_NGROK_URL")
    if frontend_ngrok_url:
        cors_origins.append(frontend_ngrok_url)
        print(f"Added frontend ngrok URL to CORS: {frontend_ngrok_url}")
    
    backend_ngrok_url = os.environ.get("BACKEND_NGROK_URL")
    if backend_ngrok_url:
        cors_origins.append(backend_ngrok_url)
        print(f"Added backend ngrok URL to CORS: {backend_ngrok_url}")
    
    # ngrokドメインのワイルドカード許可
    cors_origins.extend([
        "https://*.ngrok-free.app",
        "https://*.ngrok.io"
    ])
    
    # 追加で環境変数から指定されたオリジンも許可
    additional_origins = os.environ.get("ADDITIONAL_CORS_ORIGINS", "").split(",")
    cors_origins.extend([origin.strip() for origin in additional_origins if origin.strip()])
    
    print("Final CORS origins:", cors_origins)
    print("=========================")
    
    return cors_origins

# 開発環境ではより柔軟な設定、本番環境では厳密な設定
if os.environ.get("ENVIRONMENT", "development") == "development":
    cors_origins = get_cors_origins()
else:
    # 本番環境: 厳密な設定
    cors_origins = get_cors_origins()

# FastAPIアプリケーションの作成
app = FastAPI()

# CORSミドルウェアを追加
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"^https://[a-z0-9.-]+\\.ngrok-free\\.app$|^https://[a-z0-9.-]+\\.ngrok\\.io$|^https://[a-z0-9.-]+\\.vercel\\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# ヘルスチェックエンドポイント
@app.get("/health")
async def health_check():
    """コンテナのヘルスチェック用エンドポイント"""
    return {"status": "healthy", "message": "Application is running"}


# Supabase Keep-alive エンドポイント（認証不要）
@app.get("/keepalive")
async def keepalive():
    """
    Supabase無料プランのDB一時停止を防ぐためのkeep-aliveエンドポイント。
    DBに軽量なクエリを発行してコネクションプールをアクティブに保つ。
    GitHub Actions cronから定期的に呼び出される。
    """
    from .db_helper import get_db
    try:
        async with get_db() as conn:
            await conn.execute("SELECT 1")
        return {"status": "ok", "message": "Database connection healthy"}
    except Exception as e:
        from fastapi import Response
        return Response(
            content='{"status": "error", "message": "Database connection failed"}',
            status_code=503,
            media_type="application/json"
        )


# ルーターを定義（全ルートで有効なSupabase JWT + 許可済みメールアドレスを要求）
router = APIRouter(dependencies=[Depends(get_current_user)])

@router.get("/sessions")
async def get_sessions():
    return await fetch_sessions()

@router.post("/sessions")
async def create_session(payload: dict):
    # asyncpg requires datetime instances for TIMESTAMP columns (not ISO strings)
    now = datetime.now()
    now_iso = now.isoformat(sep=' ', timespec='milliseconds')
    session_id = str(uuid4())
    name = payload.get('name', f"セッション")
    session = {
        'session_id': session_id,
        'created_at': now,
        'updated_at': now,
        'correction_count': 0,
        'is_open': True,
        'name': name,
    }
    await insert_session(session)
    # Return camelCase for frontend
    return {
        'sessionId': session_id,
        'createdAt': now_iso,
        'updatedAt': now_iso,
        'correctionCount': 0,
        'isOpen': True,
        'name': name,
    }

@router.get("/sessions/{session_id}/histories")
async def get_histories(session_id: str):
    return await fetch_histories_by_session(session_id)

@router.post("/histories")
async def create_history(payload: dict = Body(...)):
    from uuid import uuid4
    from datetime import datetime
    # asyncpg requires datetime instances for TIMESTAMP columns (not ISO strings)
    now = datetime.now()
    now_iso = now.isoformat(sep=' ', timespec='milliseconds')
    try:
        history = {
            'history_id': payload.get('historyId', str(uuid4())),
            'session_id': payload.get('sessionId'),
            'timestamp': now,
            'original_text': payload.get('originalText'),
            'instruction_prompt': payload.get('instructionPrompt'),
            'target_text': payload.get('targetText'),
            'combined_comment': payload.get('combinedComment'),
            'selected_proposal_ids': payload.get('selectedProposalIds'),
            'custom_proposals': payload.get('customProposals'),
        }
        # 必須項目チェック
        if not history['session_id'] or not history['original_text'] or not history['target_text']:
            print(f"[create_history] Missing required field in payload: {payload}")
            return {"error": "Missing required field in payload", "payload": payload}
    except Exception as e:
        print(f"[create_history] Exception: {e}, payload: {payload}")
        return {"error": str(e), "payload": payload}

    created = await insert_history(history)
    # Serialize timestamp as ISO string for the frontend
    if isinstance(created.get('timestamp'), datetime):
        created['timestamp'] = now_iso
    return created

@router.get("/histories/{history_id}/proposals")
async def get_proposals(history_id: str):
    return await fetch_proposals_by_history(history_id)

@router.post("/proposals")
async def create_proposal(payload: dict = Body(...)):
    from uuid import uuid4
    proposal = {
        'proposalId': payload.get('proposalId', str(uuid4())),
        'historyId': payload['historyId'],
        'type': payload['type'],
        'originalAfterText': payload['originalAfterText'],
        'originalReason': payload.get('originalReason'),
        'modifiedAfterText': payload.get('modifiedAfterText'),
        'modifiedReason': payload.get('modifiedReason'),
        'isSelected': payload.get('isSelected', False),
        'isModified': payload.get('isModified', False),
        'isCustom': payload.get('isCustom', False),
        'selectedOrder': payload.get('selectedOrder')
    }
    return await insert_proposal(proposal)

@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    await db_delete_session(session_id)
    return {"message": "Session archived", "sessionId": session_id}

@router.put("/sessions/{session_id}")
async def update_session(session_id: str, payload: dict = Body(...)):
    await db_update_session(session_id, payload)
    return {"message": "Session updated", "sessionId": session_id, **payload}

@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    session = await db_fetch_session(session_id)
    if session:
        return {
            "sessionId": session["sessionId"],
            "name": session["name"],
            "createdAt": session["createdAt"],
            "correctionCount": session.get("correctionCount", 0)
        }
    return {"error": "Session not found", "sessionId": session_id}

# ルーターをアプリに含める（/health を除く全ルートに get_current_user 依存関係が適用される）
# NOTE: AI提案生成（旧 POST /suggestions）はクライアントサイドWebLLMに移行済み
# backend/app/main.py からGemini関連コード・エンドポイントは完全に削除されました
app.include_router(router)
