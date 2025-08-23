import os
import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture(autouse=True)
def set_real_mode(monkeypatch):
    monkeypatch.setenv("BACKEND_MODE", "real")

# /histories エンドポイントに履歴を保存し、ログに session_id が正しく出力されるか確認する
# DBに保存される件数も確認できるようにする

def test_create_history_and_check_session_id(capfd):
    payload = {
        "historyId": "test-history-uuid",
        "sessionId": "test-session-uuid",
        "originalText": "テストの原文",
        "targetText": "テストの修正版",
        "instructionPrompt": "丁寧な日本語に直してください",
        "combinedComment": "全体コメント",
        "selectedProposalIds": [],
        "customProposals": []
    }
    with TestClient(app) as client:
        response = client.post("/histories", json=payload)
        assert response.status_code == 200
        # 標準出力のログを取得
        out, err = capfd.readouterr()
        print("=== LOG OUTPUT ===")
        print(out)
        # session_idがログに出ているか確認
        assert "session_id" in out or "sessionId" in out
        # DBに保存された件数を確認
        response2 = client.get(f"/sessions")
        assert response2.status_code == 200
        sessions = response2.json()
        found = False
        for s in sessions:
            if s["sessionId"] == "test-session-uuid":
                found = True
                # correctionCountが1以上であること
                assert s["correctionCount"] >= 1
        assert found, "Session not found in /sessions response"
