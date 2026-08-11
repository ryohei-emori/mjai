import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from uuid import uuid4
from pathlib import Path
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# 環境変数からアプリケーションルートを取得
# Docker: APP_ROOT=/app, ローカル: 未設定時は __file__ から推測
app_root = os.environ.get("APP_ROOT")
if not app_root:
    # ローカル開発: backend/app/main.py → backend/ を app_root とする
    app_root = str(Path(__file__).resolve().parent.parent)

# .env の探索候補
_env_candidates = [
    os.path.join(app_root, "..", "conf", ".env"),  # backend/../conf/.env (ローカル開発)
    os.path.join(app_root, ".env"),                # backend/.env (ローカル開発)
    "/conf/.env",                                  # Docker 直接マウント
    str(Path(__file__).resolve().parent.parent.parent / "conf" / ".env"),  # repo/conf/.env 絶対パス
]
_env_loaded = False
for _path in _env_candidates:
    if os.path.exists(_path):
        load_dotenv(dotenv_path=_path, override=False)
        _env_loaded = True
        break

if not _env_loaded:
    print(f"[main.py] Warning: No .env file found in candidates: {_env_candidates}")

from .db_helper import (
    fetch_sessions, insert_session, 
    delete_session as db_delete_session, 
    update_session as db_update_session, 
    fetch_session as db_fetch_session,
    fetch_histories_by_session, insert_history,
    fetch_proposals_by_history, insert_proposal,
    archive_history as db_archive_history,
)
from uuid import uuid4
from datetime import datetime
from fastapi import APIRouter
from fastapi import Body, Depends, HTTPException

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

# ヘルスチェックエンドポイント (Vercelでは /api/health でアクセスされる)
@app.get("/health")
@app.get("/api/health")
async def health_check():
    """コンテナのヘルスチェック用エンドポイント"""
    return {"status": "healthy", "message": "Application is running"}


# Supabase Keep-alive エンドポイント（認証不要）
# Vercelでは /api/keepalive でアクセスされる
@app.get("/keepalive")
@app.get("/api/keepalive")
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
        # NOTE: this must raise (not `return {"error": ...}`) so the response is a
        # non-2xx status the frontend's apiFetch() treats as a failure. Previously
        # this returned 200 OK with an error-shaped body; historyAPI.createHistory()
        # then resolved successfully with no `historyId` field, and the caller
        # (saveCorrections()) went on to call proposalAPI.createProposal() with
        # `historyId: undefined` for every suggestion — JSON.stringify drops
        # undefined-valued keys, so the backend received no "historyId" key at all
        # and crashed with an unhandled KeyError (surfaced to the user as a generic
        # browser "Failed to fetch" on the /proposals request, with no indication
        # the real problem was the earlier /histories call).
        if not history['session_id'] or not history['original_text'] or not history['target_text']:
            print(f"[create_history] Missing required field in payload: {payload}")
            raise HTTPException(status_code=400, detail="Missing required field in payload (sessionId, originalText, targetText)")
    except HTTPException:
        raise
    except Exception as e:
        print(f"[create_history] Exception: {e}, payload: {payload}")
        raise HTTPException(status_code=400, detail=str(e))

    created = await insert_history(history)
    # Serialize timestamp as ISO string for the frontend
    if isinstance(created.get('timestamp'), datetime):
        created['timestamp'] = now_iso
    return created

@router.delete("/histories/{history_id}")
async def archive_history(history_id: str):
    await db_archive_history(history_id)
    return {"message": "History archived", "historyId": history_id}

@router.get("/histories/{history_id}/proposals")
async def get_proposals(history_id: str):
    return await fetch_proposals_by_history(history_id)

@router.post("/proposals")
async def create_proposal(payload: dict = Body(...)):
    from uuid import uuid4
    # Validate required keys explicitly instead of raw dict indexing: a missing
    # key previously raised an unhandled KeyError -> 500 with no clear message,
    # which surfaces to the browser as an opaque "TypeError: Failed to fetch".
    # `originalAfterText` may legitimately be "" (empty string is a valid,
    # meaningful value here - see test_create_proposal_preserves_empty_string_
    # content_fields), so only its *absence* (None/missing key) is invalid;
    # `historyId`/`type` reject both absence and "" since neither is ever a
    # meaningful empty value (a blank history FK or proposal type is always a bug).
    missing = [k for k in ("historyId", "type", "originalAfterText") if payload.get(k) is None]
    empty_invalid = [k for k in ("historyId", "type") if payload.get(k) == "" and k not in missing]
    if missing or empty_invalid:
        raise HTTPException(status_code=400, detail=f"Missing required field(s) in payload: {', '.join(missing + empty_invalid)}")
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

# AI提案生成エンドポイント
@router.post("/suggestions")
async def generate_ai_suggestions(payload: dict = Body(...)):
    """
    Generate AI correction suggestions using cloud LLM providers.
    Primary: Groq (fast), Fallback: Cloudflare Workers AI.
    WebLLM remains available on frontend as offline fallback.
    """
    from .llm import generate_suggestions
    from .llm.suggestions import SuggestionsError, NoProvidersConfiguredError
    from fastapi.responses import JSONResponse
    
    original_text = payload.get("originalText", "")
    target_text = payload.get("targetText", "")
    
    if not original_text or not target_text:
        return JSONResponse(
            status_code=400,
            content={"error": "originalText and targetText are required", "fallback_available": True}
        )
    
    try:
        result = await generate_suggestions(original_text, target_text)
        return result
    except NoProvidersConfiguredError as e:
        return JSONResponse(
            status_code=503,
            content={
                "error": str(e),
                "fallback_available": True,
                "message": "LLM providers not configured. Use WebLLM offline mode."
            }
        )
    except SuggestionsError as e:
        return JSONResponse(
            status_code=503,
            content={
                "error": str(e),
                "groq_error": e.groq_error,
                "cf_error": e.cf_error,
                "fallback_available": True,
                "message": "All cloud providers failed. Try WebLLM offline mode."
            }
        )


# ルーターをアプリに含める（/health を除く全ルートに get_current_user 依存関係が適用される）
# AI提案生成: POST /suggestions でクラウドLLM (Groq/Cloudflare) を使用
# WebLLMはフロントエンドでオフラインフォールバックとして残存
# Vercelデプロイではフロントエンドから /api/* でアクセスされるため、両方のプレフィックスで登録
app.include_router(router)
app.include_router(router, prefix="/api")
