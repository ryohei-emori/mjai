import os
import pytest
from fastapi.testclient import TestClient
from app.main import app
from pathlib import Path
from dotenv import load_dotenv

# 環境変数からアプリケーションルートを取得
app_root = os.environ.get("APP_ROOT", "/app")
conf_path = os.path.join(app_root, "..", "conf", ".env")

# conf/.envから環境変数を読み込み
load_dotenv(dotenv_path=conf_path)


@pytest.fixture(autouse=True)
def set_real_mode(monkeypatch):
    monkeypatch.setenv("BACKEND_MODE", "real")


@pytest.mark.skipif(not os.environ.get("GEMINI_API_KEY"), reason="GEMINI_API_KEY not set")
def test_generate_suggestions_gemini():
    payload = {
        "originalText": "今日は天気がいいです",
        "targetText": "今日は天気が良いです",
        "instructionPrompt": "丁寧な日本語に直してください",
        "sessionId": "test-session-gemini",
        "engine": "gemini"
    }
    with TestClient(app) as client:
        response = client.post("/suggestions", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data
        assert "overallComment" in data
        assert isinstance(data["suggestions"], list)
        # 新しい形式では指摘箇所のみなので、originalとreasonが存在する
        if len(data["suggestions"]) > 0:
            suggestion = data["suggestions"][0]
            assert "original" in suggestion
            assert "reason" in suggestion 