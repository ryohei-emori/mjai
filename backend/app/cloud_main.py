#!/usr/bin/env python3
"""
Qwen 3 クラウドAPI対応版
Alibaba Cloud DashScope APIを使用してQwen 3モデルを利用
"""

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
import httpx
import json
import re
from dotenv import load_dotenv

# .env.cloudファイルを読み込み
env_path = Path(__file__).parent.parent / ".env.cloud"
if env_path.exists():
    load_dotenv(env_path)
    print(f"[Config] Loaded environment from {env_path}")
else:
    print(f"[Config] {env_path} not found, using system environment variables")

app = FastAPI()

# CORS（フロントエンドとローカルで動かすため）
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://172.22.178.95:3000",  # LANアクセス用
        "http://0.0.0.0:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

class CorrectionSuggestion(BaseModel):
    id: str
    original: str
    corrected: str
    reason: str

class SuggestionRequest(BaseModel):
    originalText: str
    targetText: str
    instructionPrompt: Optional[str] = None
    sessionId: Optional[str] = None

class SuggestionResponse(BaseModel):
    suggestions: List[CorrectionSuggestion]
    overallComment: str
    sessionId: str

# Qwen 3 クラウドAPI設定
QWEN_CLOUD_API_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
QWEN_CLOUD_API_KEY = os.environ.get("QWEN_CLOUD_API_KEY", "")

# システムプロンプト・few shot例
SYSTEM_PROMPT = """あなたは日本語の文章校正AIです。与えられた原文と添削対象を比較し、自然で丁寧な日本語に添削してください。

重要な指示:
1. 回答は必ずJSON形式で出力してください
2. プロンプトの内容は出力に含めないでください
3. 具体的で実用的な修正案を提示してください
4. 理由は簡潔で分かりやすく説明してください"""

FEW_SHOT_EXAMPLES = """
原文: 今日は天気がいいです
添削対象: 今日は天気が良いです
修正案: 今日は天気が良いです
理由: 「いい」は「良い」と漢字表記が一般的です

原文: 彼は走って学校に行った
添削対象: 彼は走って学校へ行った
修正案: 彼は走って学校へ行った
理由: 「に」より「へ」の方が目的地を強調できます

原文: とても美味しかったです
添削対象: とてもおいしかったです
修正案: とてもおいしかったです
理由: 「美味しい」は「おいしい」とひらがな表記が一般的です
"""

# セッションごとのメモリ管理
session_memories: Dict[str, List[str]] = {}

# Qwen 3 の最新モデル選択肢
QWEN3_MODELS = {
    "qwen3-0.6b-instruct": {
        "name": "qwen3-0.6b-instruct",
        "description": "Qwen 3 0.6B Instruct (軽量、高速)",
        "size": "0.6B",
        "performance": "中",
        "memory": "低"
    },
    "qwen3-1.5b-instruct": {
        "name": "qwen3-1.5b-instruct", 
        "description": "Qwen 3 1.5B Instruct (軽量、バランス)",
        "size": "1.5B",
        "performance": "中",
        "memory": "低"
    },
    "qwen3-3b-instruct": {
        "name": "qwen3-3b-instruct",
        "description": "Qwen 3 3B Instruct (バランス)",
        "size": "3B",
        "performance": "高",
        "memory": "中"
    },
    "qwen3-7b-instruct": {
        "name": "qwen3-7b-instruct",
        "description": "Qwen 3 7B Instruct (推奨: バランスが良い)",
        "size": "7B",
        "performance": "高",
        "memory": "中"
    },
    "qwen3-14b-instruct": {
        "name": "qwen3-14b-instruct",
        "description": "Qwen 3 14B Instruct (高性能)",
        "size": "14B",
        "performance": "非常に高",
        "memory": "高"
    },
    "qwen3-32b-instruct": {
        "name": "qwen3-32b-instruct",
        "description": "Qwen 3 32B Instruct (最高性能)",
        "size": "32B",
        "performance": "最高",
        "memory": "非常に高"
    },
    "qwen3-30b-a3b-instruct": {
        "name": "qwen3-30b-a3b-instruct",
        "description": "Qwen 3 30B-A3B Instruct (MoEモデル)",
        "size": "30B-A3B",
        "performance": "非常に高",
        "memory": "高"
    },
    "qwen3-235b-a22b-instruct": {
        "name": "qwen3-235b-a22b-instruct",
        "description": "Qwen 3 235B-A22B Instruct (最高性能MoE)",
        "size": "235B-A22B",
        "performance": "最高",
        "memory": "非常に高"
    }
}

@asynccontextmanager
async def lifespan(app):
    """アプリケーションのライフサイクル管理"""
    if not QWEN_CLOUD_API_KEY:
        print("⚠️  Warning: QWEN_CLOUD_API_KEY not set")
        print("環境変数を設定してください: export QWEN_CLOUD_API_KEY='your-api-key'")
        app.state.api_available = False
    else:
        print(f"[Qwen 3 Cloud API] API Key configured")
        app.state.api_available = True
    
    yield

app = FastAPI(lifespan=lifespan)

async def call_qwen_cloud_api(prompt: str, model_name: str = "qwen3-7b-instruct") -> str:
    """Qwen 3 クラウドAPIを呼び出す"""
    if not QWEN_CLOUD_API_KEY:
        return ""
    
    headers = {
        "Authorization": f"Bearer {QWEN_CLOUD_API_KEY}",
        "Content-Type": "application/json"
    }
    
    selected_model = QWEN3_MODELS.get(model_name, QWEN3_MODELS["qwen3-7b-instruct"])["name"]
    
    payload = {
        "model": selected_model,
        "input": {
            "messages": [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ]
        },
        "parameters": {
            "max_tokens": 1024,
            "temperature": 0.7,
            "top_p": 0.9,
            "result_format": "message"  # JSON形式での出力を促進
        }
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(QWEN_CLOUD_API_URL, headers=headers, json=payload)
            response.raise_for_status()
            
            result = response.json()
            if "output" in result and "choices" in result["output"]:
                content = result["output"]["choices"][0]["message"]["content"]
                print(f"[Qwen 3 Cloud API] Model: {selected_model}")
                print(f"[Qwen 3 Cloud API] Response: {content}")
                return content
            else:
                print(f"[Qwen 3 Cloud API] Unexpected response format: {result}")
                return ""
                
    except Exception as e:
        print(f"[Qwen 3 Cloud API] Error: {e}")
        return ""

def parse_json_response(response_text: str) -> tuple[List[Dict], str]:
    """API応答からJSONを解析して修正案と全体コメントを抽出"""
    try:
        # JSON部分を抽出
        match = re.search(r'\{\s*"suggestions".*\}', response_text, re.DOTALL)
        if match:
            parsed = json.loads(match.group(0))
            suggestions = parsed.get("suggestions", [])
            overall_comment = parsed.get("overallComment", "")
            return suggestions, overall_comment
    except Exception as e:
        print(f"[JSON Parse Error] {e}")
    
    return [], ""

@app.post("/suggestions", response_model=SuggestionResponse)
async def generate_suggestions(req: SuggestionRequest, request: Request):
    """文章校正の提案を生成"""
    # セッションID管理
    session_id = req.sessionId or str(uuid4())
    if session_id not in session_memories:
        session_memories[session_id] = []

    # APIが利用可能かチェック
    if not request.app.state.api_available:
        # モックデータを返す
        mock_suggestions = [
            CorrectionSuggestion(
                id="1",
                original="私は学校に行きました",
                corrected="私は学校へ行きました",
                reason="移動の方向を表す場合は「へ」が適切です"
            ),
            CorrectionSuggestion(
                id="2",
                original="とても美味しかったです",
                corrected="とてもおいしかったです",
                reason="「美味しい」は「おいしい」とひらがな表記が一般的です"
            ),
            CorrectionSuggestion(
                id="3",
                original="友達と一緒に遊んだ",
                corrected="友達と一緒に遊びました",
                reason="丁寧語で統一した方が自然です"
            ),
        ]
        mock_overall_comment = "APIキーが設定されていないため、モックデータを返しています。"
        return SuggestionResponse(suggestions=mock_suggestions, overallComment=mock_overall_comment, sessionId=session_id)

    # プロンプト生成
    memory_text = "\n".join(session_memories[session_id][-5:])  # 直近5件だけ
    prompt = f"""{FEW_SHOT_EXAMPLES}

{memory_text}

原文: {req.originalText}
添削対象: {req.targetText}

以下のJSON形式で回答してください。プロンプトの内容は含めず、JSONのみを出力してください：

{{
  "suggestions": [
    {{
      "id": "1",
      "original": "修正前の文章",
      "corrected": "修正後の文章", 
      "reason": "修正理由"
    }}
  ],
  "overallComment": "全体的なコメント"
}}"""

    # 使用するモデルを環境変数から取得（デフォルトは7B）
    model_name = os.environ.get("QWEN3_MODEL", "qwen3-7b-instruct")
    
    # Qwen 3 クラウドAPIを呼び出し
    result = await call_qwen_cloud_api(prompt, model_name)
    
    if result:
        # JSON解析
        suggestions_data, overall_comment = parse_json_response(result)
        
        if suggestions_data:
            # 修正案を変換
            suggestions = []
            for i, s in enumerate(suggestions_data):
                suggestion = CorrectionSuggestion(
                    id=str(i + 1),
                    original=s.get("original", ""),
                    corrected=s.get("corrected", ""),
                    reason=s.get("reason", "")
                )
                suggestions.append(suggestion)
            
            return SuggestionResponse(
                suggestions=suggestions, 
                overallComment=overall_comment, 
                sessionId=session_id
            )
    
    # フォールバック: モックデータ
    mock_suggestions = [
        CorrectionSuggestion(
            id="1",
            original="私は学校に行きました",
            corrected="私は学校へ行きました",
            reason="移動の方向を表す場合は「へ」が適切です"
        ),
        CorrectionSuggestion(
            id="2",
            original="とても美味しかったです",
            corrected="とてもおいしかったです",
            reason="「美味しい」は「おいしい」とひらがな表記が一般的です"
        ),
    ]
    mock_overall_comment = "API応答の解析に失敗したため、モックデータを返しています。"
    return SuggestionResponse(suggestions=mock_suggestions, overallComment=mock_overall_comment, sessionId=session_id)

@app.get("/models")
async def get_available_models():
    """利用可能なQwen 3モデルの一覧を取得"""
    return {
        "models": QWEN3_MODELS,
        "current_model": os.environ.get("QWEN3_MODEL", "qwen3-7b-instruct"),
        "api_available": True if QWEN_CLOUD_API_KEY else False
    }

@app.get("/health")
async def health_check():
    """ヘルスチェック"""
    return {
        "status": "healthy",
        "api_available": True if QWEN_CLOUD_API_KEY else False,
        "current_model": os.environ.get("QWEN3_MODEL", "qwen3-7b-instruct")
    } 