import os
import sys
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional, Dict
from fastapi.middleware.cors import CORSMiddleware
from uuid import uuid4
from pathlib import Path
from fastapi import Request
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
    # PostgreSQL 用（未マイグレーション完全化）
    fetch_sessions, insert_session, 
    delete_session as db_delete_session, 
    update_session as db_update_session, 
    fetch_session as db_fetch_session,
    fetch_histories_by_session, insert_history,
    fetch_proposals_by_history, insert_proposal,
    # SQLite 用（現在のスキーマと整合）
    fetch_sessions_sqlite, insert_session_sqlite,
    delete_session_sqlite, update_session_sqlite,
    fetch_session_sqlite, fetch_histories_by_session_sqlite,
    insert_history_sqlite, fetch_proposals_by_history_sqlite,
    insert_proposal_sqlite
)
from uuid import uuid4
from datetime import datetime
from fastapi import APIRouter
from fastapi import Body
import requests

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
    print(f"FRONTEND_NGROK_URL: {os.environ.get('FRONTEND_NGROK_URL')}")
    print(f"BACKEND_NGROK_URL: {os.environ.get('BACKEND_NGROK_URL')}")
    
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
    allow_origin_regex=r"^https://[a-z0-9.-]+\\.ngrok-free\\.app$|^https://[a-z0-9.-]+\\.ngrok\\.io$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# ヘルスチェックエンドポイント
@app.get("/health")
async def health_check():
    """コンテナのヘルスチェック用エンドポイント"""
    return {"status": "healthy", "message": "Application is running"}

# Pydanticモデルの定義
class CorrectionSuggestion(BaseModel):
    id: str
    original: str
    reason: str

class SuggestionRequest(BaseModel):
    originalText: str
    targetText: str
    instructionPrompt: Optional[str] = None
    sessionId: Optional[str] = None
    engine: Optional[str] = None

class SuggestionResponse(BaseModel):
    suggestions: List[CorrectionSuggestion]
    overallComment: str
    sessionId: str

# システムプロンプト・few shot例（あとで編集しやすいように分離）
SYSTEM_PROMPT = """あなたは日本語または中国から中国語または日本語に翻訳された文を校閲するプロフェッショナルです。json形式で、中国語で回答してください。次の例にしたがって、日本語または中国語から中国語または日本語へ翻訳を試みた文を対象に、json形式で中国語で原文の意味から誤っている箇所を５つ指摘し、修正の方向性をコメントして、中国語で全体講評を行ってください。ただし、次の回答形式の条件を満たすこと

## 条件
- json形式で回答
- 中国語で回答
- 指摘例の回答形式の構造・分量に従う
- 全体講評の口調・分量に従う
- 全体講評は、「加油〜」で終える
"""

FEW_SHOT_EXAMPLES = """
## 例
＜中国語または日本語に翻訳する日本語または中国語の文＞筆者は以前、早期教育の幼児教室で働いていたことでした。保護者からよく「この教室に通わせたらどのような大人になるのか」と聞かれました。答えようがありませんでした。大人になるのは様々な要因が積み重なり絡み合ったことです。遺伝、家庭環境、友達及びどんな担任にあったかなどです。

授業中、小さな子をいじめるなど問題行為を起こす子供がいました。お母親がお迎えにいらした時そのことを伝えました。「でもうちの子は文字と数字が大好きで、お勉強ができるんだ」と反論されました。優秀だと思っていた我が子を指摘されて、気分を害したかもしれない。「幼い頃算盤をやらせて計算能力が高くなった」とか「幼い頃絵本を沢山読み聞かせたから、読書家となり国語成績がよくなった」など、一定の側面は程度の結果が出るが、「勉強ができるかできないか」と「人としてやって悪いことよいことを教育する」は別次元のことからです。

＜日本語または中国語の文から中国語または日本語に翻訳を試みた文＞笔者以前=辻早教班的老姉。学生家本経常向我"在个班学，我家孩子会変成怎祥的大人呢？"我并不想回复。成为大人是由各种原因纵横交错而成，比方说遗传、家庭环境、友情以及工作等因素。

在我的课上，有个孩子霸凌年纪比较小的孩子。这个孩子妈妈来接他的时候，我将这件事告诉这孩子的妈妈。或许这位妈妈听完我讲的话心情不好受，想着我竟然去批评她那么优秀的孩子。反驳我道："我家孩子非常喜欢文字和数字，学习可厉害了。"虽然，"从小就让孩子学算盘所以孩子计算能力很强"、"从小就让孩子看很多绘本，作为阅读小能手语文成绩很好。"这些从一定的侧面来说早教是有所成果的。但是这些和"会不会学习"、"教育孩子作为人哪些可＊哪些不可"来説完全是两事

＜日本語または中国語の文から中国語または日本語に翻訳を試みた文に対する誤りの指摘＞
{
  "指摘": [
    {
      "番号": 1,
      "箇所": "我并不想回复",
      "コメント": "ようがない并非不想的含义，这里可以再看一下这个文法的含义\nようがない：〜できない / 〜したくても手段がない\n不可能であることを强调して言う時に使う。"
    },
    {
      "番号": 2,
      "箇所": "どんな担任にあったか",
      "コメント": "担任指的是学校的老师哦\n担任：学校で，教師があるクラス・教科などを受け持つこと。また，その教師。"
    },
    {
      "番号": 3,
      "箇所": "有个孩子霸凌年纪比较小的孩子",
      "コメント": "这里最好把問題行為译出来哦"
    }
  ],
  "全体講評": "译文整体的流畅性和对原意翻译处理和展现比较不错，可以再看一下以上几点，注意积累一下ようがない和担任的含义，加油～"
}
"""

# セッションごとのメモリ管理（簡易実装: メモリはプロセス内辞書で保持）
session_memories: Dict[str, List[str]] = {}

# ルーターを定義
router = APIRouter()

@router.get("/sessions")
async def get_sessions():
    try:
        # 環境変数でデータベースの切り替えを制御
        if os.environ.get("USE_POSTGRESQL", "true").lower() == "true":
            return await fetch_sessions()
        # フォールバック：SQLite（明示的にfalseのときのみ）
        return fetch_sessions_sqlite()
    except Exception as e:
        if os.environ.get("USE_POSTGRESQL", "true").lower() == "true":
            # フォールバック禁止: Supabase失敗時はエラーを返す
            print(f"[ERROR] Supabase fetch_sessions failed: {e}")
            raise
        else:
            print(f"[WARN] fetch_sessions failed, fallback to SQLite: {e}")
            return fetch_sessions_sqlite()

@router.post("/sessions")
async def create_session(payload: dict):
    now = datetime.now().isoformat(sep=' ', timespec='milliseconds')
    session = {
        'sessionId': str(uuid4()),
        'createdAt': now,
        'updatedAt': now,
        'name': payload.get('name', f"セッション"),
        'correctionCount': 0,
        'isOpen': True
    }
    try:
        if os.environ.get("USE_POSTGRESQL", "true").lower() == "true":
            return await insert_session(session)
        insert_session_sqlite(session)
        return session
    except Exception as e:
        if os.environ.get("USE_POSTGRESQL", "true").lower() == "true":
            print(f"[ERROR] Supabase insert_session failed: {e}")
            raise
        else:
            print(f"[WARN] insert_session failed, fallback to SQLite: {e}")
            insert_session_sqlite(session)
            return session

@router.get("/sessions/{session_id}/histories")
async def get_histories(session_id: str):
    try:
        if os.environ.get("USE_POSTGRESQL", "true").lower() == "true":
            return await fetch_histories_by_session(session_id)
        return fetch_histories_by_session_sqlite(session_id)
    except Exception as e:
        if os.environ.get("USE_POSTGRESQL", "true").lower() == "true":
            print(f"[ERROR] Supabase fetch_histories failed: {e}")
            raise
        else:
            print(f"[WARN] fetch_histories failed, fallback to SQLite: {e}")
            return fetch_histories_by_session_sqlite(session_id)

@router.post("/histories")
async def create_history(payload: dict = Body(...)):
    from uuid import uuid4
    from datetime import datetime
    now = datetime.now().isoformat(sep=' ', timespec='milliseconds')
    try:
        # snake_case & camelCase両対応
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
            # SQLite用camelCase
            'historyId': payload.get('historyId', str(uuid4())),
            'sessionId': payload.get('sessionId'),
            'originalText': payload.get('originalText'),
            'instructionPrompt': payload.get('instructionPrompt'),
            'targetText': payload.get('targetText'),
            'combinedComment': payload.get('combinedComment'),
            'selectedProposalIds': payload.get('selectedProposalIds'),
            'customProposals': payload.get('customProposals')
        }
        # 必須項目チェック
        if not history['session_id'] or not history['original_text'] or not history['target_text']:
            print(f"[create_history] Missing required field in payload: {payload}")
            return {"error": "Missing required field in payload", "payload": payload}
    except Exception as e:
        print(f"[create_history] Exception: {e}, payload: {payload}")
        return {"error": str(e), "payload": payload}
    try:
        if os.environ.get("USE_POSTGRESQL", "true").lower() == "true":
            return await insert_history(history)
        return insert_history_sqlite(history) or history
    except Exception as e:
        if os.environ.get("USE_POSTGRESQL", "true").lower() == "true":
            print(f"[ERROR] Supabase insert_history failed: {e}")
            raise
        else:
            print(f"[WARN] insert_history failed, fallback to SQLite: {e}")
            return insert_history_sqlite(history) or history

@router.get("/histories/{history_id}/proposals")
async def get_proposals(history_id: str):
    try:
        if os.environ.get("USE_POSTGRESQL", "true").lower() == "true":
            return await fetch_proposals_by_history(history_id)
        return fetch_proposals_by_history_sqlite(history_id)
    except Exception as e:
        if os.environ.get("USE_POSTGRESQL", "true").lower() == "true":
            print(f"[ERROR] Supabase fetch_proposals failed: {e}")
            raise
        else:
            print(f"[WARN] fetch_proposals failed, fallback to SQLite: {e}")
            return fetch_proposals_by_history_sqlite(history_id)

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
        'isSelected': payload.get('isSelected', 0),
        'isModified': payload.get('isModified', 0),
        'isCustom': payload.get('isCustom', 0),
        'selectedOrder': payload.get('selectedOrder')
    }
    try:
        if os.environ.get("USE_POSTGRESQL", "true").lower() == "true":
            return await insert_proposal(proposal)
        return insert_proposal_sqlite(proposal) or proposal
    except Exception as e:
        if os.environ.get("USE_POSTGRESQL", "true").lower() == "true":
            print(f"[ERROR] Supabase insert_proposal failed: {e}")
            raise
        else:
            print(f"[WARN] insert_proposal failed, fallback to SQLite: {e}")
            return insert_proposal_sqlite(proposal) or proposal

@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    try:
        if os.environ.get("USE_POSTGRESQL", "true").lower() == "true":
            await db_delete_session(session_id)
            return {"message": "Session deleted", "sessionId": session_id}
        delete_session_sqlite(session_id)
        return {"message": "Session deleted", "sessionId": session_id}
    except Exception as e:
        if os.environ.get("USE_POSTGRESQL", "true").lower() == "true":
            print(f"[ERROR] Supabase delete_session failed: {e}")
            raise
        else:
            print(f"[WARN] delete_session failed, fallback to SQLite: {e}")
            try:
                delete_session_sqlite(session_id)
                return {"message": "Session deleted (fallback)", "sessionId": session_id}
            except Exception as e2:
                return {"error": f"Failed to delete session: {str(e2)}", "sessionId": session_id}

@router.put("/sessions/{session_id}")
async def update_session(session_id: str, payload: dict = Body(...)):
    try:
        if os.environ.get("USE_POSTGRESQL", "true").lower() == "true":
            await db_update_session(session_id, payload)
            return {"message": "Session updated", "sessionId": session_id, **payload}
        update_session_sqlite(session_id, payload)
        return {"message": "Session updated", "sessionId": session_id, **payload}
    except Exception as e:
        if os.environ.get("USE_POSTGRESQL", "true").lower() == "true":
            print(f"[ERROR] Supabase update_session failed: {e}")
            raise
        else:
            print(f"[WARN] update_session failed, fallback to SQLite: {e}")
            try:
                update_session_sqlite(session_id, payload)
                return {"message": "Session updated (fallback)", "sessionId": session_id, **payload}
            except Exception as e2:
                return {"error": f"Failed to update session: {str(e2)}", "sessionId": session_id}

@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    try:
        if os.environ.get("USE_POSTGRESQL", "true").lower() == "true":
            session = await db_fetch_session(session_id)
            if session:
                return {
                    "sessionId": session["sessionId"],
                    "name": session["name"],
                    "createdAt": session["createdAt"],
                    "correctionCount": session.get("correctionCount", 0)
                }
            return {"error": "Session not found", "sessionId": session_id}
        session = fetch_session_sqlite(session_id)
        if session:
            return {
                "sessionId": session["sessionId"],
                "name": session["name"],
                "createdAt": session["createdAt"],
                "correctionCount": session.get("correctionCount", 0)
            }
        return {"error": "Session not found", "sessionId": session_id}
    except Exception as e:
        if os.environ.get("USE_POSTGRESQL", "true").lower() == "true":
            print(f"[ERROR] Supabase get_session failed: {e}")
            raise
        else:
            print(f"[WARN] get_session failed, fallback to SQLite: {e}")
            try:
                session = fetch_session_sqlite(session_id)
                if session:
                    return {
                        "sessionId": session["sessionId"],
                        "name": session["name"],
                        "createdAt": session["createdAt"],
                        "correctionCount": session.get("correctionCount", 0)
                    }
                return {"error": "Session not found", "sessionId": session_id}
            except Exception as e2:
                return {"error": f"Failed to get session: {str(e2)}", "sessionId": session_id}

# ルーターをアプリに含める
app.include_router(router)

# Gemini API設定
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-pro")
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

def generate_gemini_suggestions(original, target, instruction=None):
    if not GEMINI_API_KEY or not GEMINI_API_URL:
        return {"suggestions": [], "overallComment": "Gemini APIキーが設定されていません", "sessionId": ""}
    prompt = SYSTEM_PROMPT + "\n" + FEW_SHOT_EXAMPLES + "\n"
    prompt += f"## 問題\n"
    prompt += f"＜中国語または日本語にに翻訳する日本語または中国語の文＞\n{original}\n\n"
    prompt += f"＜日本語または中国語の文から中国語または日本語に翻訳を試みた文＞\n{target}\n\n"
    prompt += f"## あなたが生成する回答\n＜日本語または中国語の文から中国語または日本語に翻訳を試みた文に対する誤りの指摘＞"
    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": GEMINI_API_KEY
    }
    data = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    try:
        response = requests.post(GEMINI_API_URL, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        import re, json as pyjson
        
        # レスポンス構造を安全に処理
        resp_json = response.json()
        if "candidates" not in resp_json or not resp_json["candidates"]:
            raise KeyError("'candidates' not found or empty in response")
            
        candidate = resp_json["candidates"][0]
        if "content" not in candidate:
            raise KeyError("'content' not found in candidate")
            
        content = candidate["content"]
        if "parts" not in content or not content["parts"]:
            raise KeyError("'parts' not found in content")
            
        text = content["parts"][0]["text"]
        match = re.search(r'\{\s*"指摘".*\}', text, re.DOTALL)
        if match:
            parsed = pyjson.loads(match.group(0))
            shiteki_list = parsed.get("指摘", [])
            overall_comment = parsed.get("全体講評", "")
            
            # 新しい形式から既存のCorrectionSuggestion形式に変換
            suggestions = []
            for i, shiteki in enumerate(shiteki_list):
                suggestions.append({
                    "id": str(i+1),
                    "original": shiteki.get("箇所", ""),
                    "reason": shiteki.get("コメント", "")
                })
            
            # 5個未満なら空の提案で埋める
            for i in range(len(suggestions), 5):
                suggestions.append({
                    "id": str(i+1),
                    "original": "",
                    "reason": ""
                })
            # 5個超なら5個に切る
            suggestions = suggestions[:5]
            return {"suggestions": suggestions, "overallComment": overall_comment, "sessionId": ""}
        else:
            return {"suggestions": [{"id": str(i+1), "original": "", "reason": ""} for i in range(5)], "overallComment": "Gemini返答にJSONが見つかりませんでした", "sessionId": ""}
    except Exception as e:
        return {"suggestions": [{"id": str(i+1), "original": "", "reason": ""} for i in range(5)], "overallComment": f"Gemini APIエラー: {e}", "sessionId": ""}

@app.post("/suggestions", response_model=SuggestionResponse)
def generate_suggestions(req: SuggestionRequest, request: Request):
    mode = os.environ.get("BACKEND_MODE", "mock")
    engine = getattr(req, "engine", None) or request.query_params.get("engine")
    session_id = req.sessionId or str(uuid4())
    if session_id not in session_memories:
        session_memories[session_id] = []

    if engine == "gemini":
        result = generate_gemini_suggestions(req.originalText, req.targetText, req.instructionPrompt)
        suggestions = [CorrectionSuggestion(**s) for s in result.get("suggestions", [])]
        overall_comment = result.get("overallComment", "")
        return SuggestionResponse(suggestions=suggestions, overallComment=overall_comment, sessionId=session_id)

    if mode == "mock":
        mock_suggestions = [
            CorrectionSuggestion(
                id="1",
                original="我并不想回复",
                reason="ようがない并非不想的含义，这里可以再看一下这个文法的含义\nようがない：〜できない / 〜したくても手段がない\n不可能であることを強調して言う時に使う。"
            ),
            CorrectionSuggestion(
                id="2",
                original="どんな担任にあったか",
                reason="担任指的是学校の老师哦\n担任：学校で，教師があるクラス・教科などを受け持つこと。また，その教師。"
            ),
            CorrectionSuggestion(
                id="3",
                original="有个孩子霸凌年纪比较小的孩子",
                reason="这里最好把問題行為译出来哦"
            ),
            CorrectionSuggestion(
                id="4",
                original="",
                reason=""
            ),
            CorrectionSuggestion(
                id="5",
                original="",
                reason=""
            ),
        ]
        mock_overall_comment = "译文整体的流畅性和对原意翻译处理和展现比较不错，可以再看一下以上几点，注意积累一下ようがない和担任的含义，加油～"
        return SuggestionResponse(suggestions=mock_suggestions, overallComment=mock_overall_comment, sessionId=session_id)