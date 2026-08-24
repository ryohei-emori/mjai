import os
import sys
import time
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
    fetch_histories_by_session, insert_history, update_history,
    fetch_proposals_by_history, insert_proposal, update_proposal,
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
            # Default confirmed keeps legacy confirm-only clients working.
            'status': payload.get('status', 'confirmed'),
            'overall_comment': payload.get('overallComment'),
            'provider': payload.get('provider'),
            # Inference provenance (gemini/groq/cloudflare/webllm + exact model
            # id), distinct from `provider` which records the transport.
            'llm_provider': payload.get('llmProvider'),
            'llm_model': payload.get('llmModel'),
            'client_job_id': payload.get('clientJobId'),
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

    try:
        created = await insert_history(history)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    # Serialize timestamp as ISO string for the frontend
    if isinstance(created.get('timestamp'), datetime):
        created['timestamp'] = now_iso
    return created

@router.put("/histories/{history_id}")
async def put_history(history_id: str, payload: dict = Body(...)):
    """Promote/finalize a history (e.g. pending → confirmed) without double-insert."""
    try:
        updated = await update_history(history_id, payload or {})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not updated:
        raise HTTPException(status_code=404, detail="History not found")
    if isinstance(updated.get('timestamp'), datetime):
        updated['timestamp'] = updated['timestamp'].isoformat(sep=' ', timespec='milliseconds')
    return updated

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

@router.put("/proposals/{proposal_id}")
async def put_proposal(proposal_id: str, payload: dict = Body(...)):
    """Update selection/edit metadata on an existing proposal (confirm path)."""
    updated = await update_proposal(proposal_id, payload or {})
    if not updated:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return updated

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

# AI添削プロンプト設定（全ユーザー共通の1レコード）
@router.get("/settings/prompt")
async def get_prompt_setting_route():
    """Return the effective correction prompt, the built-in default, and attribution."""
    from .prompt_settings import get_prompt_settings
    return await get_prompt_settings()


@router.put("/settings/prompt")
async def put_prompt_setting_route(
    payload: dict = Body(...),
    user: dict = Depends(get_current_user),
):
    """Save the shared custom correction prompt (validated, attributed to the caller)."""
    from .prompt_settings import (
        PromptStoreUnavailableError,
        PromptValidationError,
        save_prompt_settings,
    )
    try:
        return await save_prompt_settings(
            payload.get("systemPrompt"),
            updated_by=(user.get("email") if isinstance(user, dict) else None),
        )
    except PromptValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PromptStoreUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.delete("/settings/prompt")
async def delete_prompt_setting_route():
    """Reset to the built-in default prompt by deleting the stored row."""
    from .prompt_settings import reset_prompt_settings
    return await reset_prompt_settings()


# AI提案生成エンドポイント
@router.post("/suggestions")
async def generate_ai_suggestions(payload: dict = Body(...)):
    """
    Generate AI correction suggestions using cloud LLM providers.
    Primary: private Codex CLI API when configured, then Gemini, Groq, and Cloudflare Workers AI.
    WebLLM remains available on frontend as offline fallback.
    """
    from .llm import generate_suggestions
    from .llm.suggestions import (
        SUGGESTIONS_WALL_CLOCK_S,
        SuggestionsError,
        NoProvidersConfiguredError,
    )
    from .llm.provider_health import (
        flush_observations,
        load_shared_state,
        seed_cooldowns,
    )
    from .prompt_settings import SETTING_KEY, prompt_override_from_row
    from fastapi.responses import JSONResponse

    # Measured from request entry, not from the first provider call: the stored
    # prompt lookup runs before generation and its seconds count against the
    # same Vercel maxDuration as the LLM calls do.
    deadline_monotonic = time.monotonic() + SUGGESTIONS_WALL_CLOCK_S

    original_text = payload.get("originalText", "")
    target_text = payload.get("targetText", "")
    # Optional 模範回答訳文: reference calibration only, never required.
    exemplar_translation = (payload.get("exemplarTranslation") or "").strip()
    codex_model = (payload.get("codexModel") or "").strip() or None
    
    if not original_text or not target_text:
        return JSONResponse(
            status_code=400,
            content={"error": "originalText and targetText are required", "fallback_available": True}
        )

    try:
        # One connection for both: the stored prompt (missing/unreadable => the
        # built-in default) and what earlier requests learned about which
        # credentials are rate-limited, so this request can route around them
        # instead of re-collecting the same 429s.
        setting_row, health_rows = await load_shared_state(SETTING_KEY)
        system_prompt_override = prompt_override_from_row(setting_row)
        seed_cooldowns(health_rows)
        try:
            result = await generate_suggestions(
                original_text,
                target_text,
                exemplar_translation,
                system_prompt_override,
                codex_model=codex_model,
                deadline_monotonic=deadline_monotonic,
            )
        finally:
            # Refusals seen here are worth the next request's while, whether this
            # one ended up succeeding on a later provider or failing outright.
            await flush_observations(deadline_monotonic)
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
        if getattr(e, "rate_limited", False):
            client_message = (
                "Cloud providers are rate-limited or quota-exhausted. "
                "The API key pool spreads load across accounts but does not raise "
                "per-account RPD/quota limits — check the Groq/Cloudflare/Gemini "
                "dashboards. Retry later, or enable WebLLM offline mode."
            )
        elif getattr(e, "timed_out", False):
            # Distinct advice: nothing is misconfigured, the chain simply ran
            # out of time, and a retry usually succeeds.
            client_message = (
                "Cloud generation ran out of time before any provider returned "
                "a usable answer. Retry, shorten the text, or enable WebLLM "
                "offline mode."
            )
        else:
            client_message = (
                "All cloud providers failed. Try WebLLM offline mode."
            )
        return JSONResponse(
            status_code=503,
            content={
                "error": str(e),
                "groq_error": e.groq_error,
                "cf_error": e.cf_error,
                "gemini_error": getattr(e, "gemini_error", None),
                "codex_error": getattr(e, "codex_error", None),
                "fallback_available": True,
                "rate_limited": bool(getattr(e, "rate_limited", False)),
                "timed_out": bool(getattr(e, "timed_out", False)),
                "groq_pool_size": int(getattr(e, "groq_pool_size", 0) or 0),
                "cf_pool_size": int(getattr(e, "cf_pool_size", 0) or 0),
                "gemini_pool_size": int(getattr(e, "gemini_pool_size", 0) or 0),
                "message": client_message,
            }
        )


# Long-running Codex path. Each request is short; the browser polls the task
# until the host-side CLI has produced the final JSON.
@router.post("/suggestions/async")
async def start_async_codex_suggestions(payload: dict = Body(...)):
    from fastapi.responses import JSONResponse
    from .llm.codexcli_provider import (
        CodexCLIError,
        get_codexcli_model,
        is_codexcli_configured,
        submit_codexcli_task,
    )
    from .llm.prompts import build_messages
    from .llm.local_fastpath import try_local_fastpath
    from .prompt_settings import SETTING_KEY, prompt_override_from_row
    from .llm.provider_health import load_shared_state

    original_text = payload.get("originalText", "")
    target_text = payload.get("targetText", "")
    if not original_text or not target_text:
        return JSONResponse(status_code=400, content={"error": "originalText and targetText are required"})
    fast_result = try_local_fastpath(original_text, target_text)
    if fast_result is not None:
        return {"status": "completed", **fast_result}
    if not is_codexcli_configured():
        return JSONResponse(status_code=404, content={"error": "Codex CLI API is not configured"})
    setting_row, _ = await load_shared_state(SETTING_KEY)
    messages = build_messages(
        original_text,
        target_text,
        (payload.get("exemplarTranslation") or "").strip(),
        prompt_override_from_row(setting_row),
    )
    requested_model = (payload.get("codexModel") or "").strip() or None
    try:
        task_id = await submit_codexcli_task(messages, model=requested_model)
    except CodexCLIError as exc:
        return JSONResponse(status_code=502, content={"error": "Codex CLI task submission failed", "codex_error": str(exc)})
    return {
        "status": "pending",
        "taskId": task_id,
        "llmProvider": "codex-cli",
        "llmModel": get_codexcli_model(requested_model),
    }


@router.get("/suggestions/async/{task_id}")
async def get_async_codex_suggestions(task_id: str):
    from fastapi.responses import JSONResponse
    from .llm.codexcli_provider import CodexCLIError, get_codexcli_model, get_codexcli_task

    try:
        task = await get_codexcli_task(task_id)
    except CodexCLIError as exc:
        return JSONResponse(status_code=502, content={"error": str(exc), "codex_error": str(exc)})
    state = task.get("state")
    if state in {"queued", "running"}:
        return {"status": "pending", "taskId": task_id, "state": state}
    if state != "completed":
        detail = task.get("error") or task.get("stderr") or state or "unknown"
        return JSONResponse(status_code=502, content={"error": "Codex CLI task failed", "codex_error": str(detail)})
    output = task.get("output_json")
    if not isinstance(output, dict):
        return JSONResponse(status_code=502, content={"error": "Codex CLI returned invalid JSON", "codex_error": "output_json was not an object"})
    return {
        **output,
        "llmProvider": "codex-cli",
        "llmModel": task.get("model") or get_codexcli_model(),
        "status": "completed",
        "taskId": task_id,
    }


# ルーターをアプリに含める（/health を除く全ルートに get_current_user 依存関係が適用される）
# AI提案生成: POST /suggestions でクラウドLLM (Gemini → Groq → Cloudflare) を使用
# WebLLMはフロントエンドでオフラインフォールバックとして残存
# Vercelデプロイではフロントエンドから /api/* でアクセスされるため、両方のプレフィックスで登録
app.include_router(router)
app.include_router(router, prefix="/api")
