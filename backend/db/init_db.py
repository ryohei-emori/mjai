import sqlite3
from pathlib import Path
import os

# DBファイルとスキーマファイルのパスを相対パスで設定（PYTHONPATH=.により相対パスでアクセス可能）
DB_PATH = Path("app.db")
SCHEMA_PATH = Path("schema.sql")

def init_db():
    """データベースを初期化する"""
    print(f"Initializing database at: {DB_PATH}")
    print(f"Using schema from: {SCHEMA_PATH}")
    
    # スキーマファイルを読み込み
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        schema = f.read()
    
    # データベースを作成・初期化
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(schema)
    conn.close()
    
    print("Database initialized successfully!")

if __name__ == '__main__':
    init_db() 