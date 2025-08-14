import sqlite3
from pathlib import Path
import os

# 環境変数からアプリケーションルートを取得
app_root = os.environ.get("APP_ROOT", "/app")
db_path = os.path.join(app_root, "db", "app.db")
schema_path = os.path.join(app_root, "db", "schema.sql")

# DBファイルとスキーマファイルのパスを環境変数から取得
DB_PATH = Path(db_path)
SCHEMA_PATH = Path(schema_path)

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