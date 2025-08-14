#!/usr/bin/env python3
"""
モデルダウンロードスクリプト
より高性能なモデルをダウンロードするためのスクリプト
"""

import os
import sys
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForCausalLM

def download_model(model_name, local_path):
    """モデルをダウンロードしてローカルに保存"""
    print(f"Downloading {model_name} to {local_path}")
    
    # ディレクトリ作成
    Path(local_path).mkdir(parents=True, exist_ok=True)
    
    try:
        # トークナイザーをダウンロード
        print("Downloading tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        tokenizer.save_pretrained(local_path)
        
        # モデルをダウンロード
        print("Downloading model...")
        model = AutoModelForCausalLM.from_pretrained(model_name)
        model.save_pretrained(local_path)
        
        print(f"✅ Successfully downloaded {model_name} to {local_path}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to download {model_name}: {e}")
        return False

def main():
    # モデル選択肢
    models = {
        "1": {
            "name": "meta-llama/Meta-Llama-3.1-8B-Instruct",
            "local_path": "models/llama-3.1-8b-instruct",
            "description": "Llama 3.1 8B Instruct (代替選択肢)"
        },
        "2": {
            "name": "elyza/ELYZA-japanese-Llama-3.1-8B-Instruct",
            "local_path": "models/elyza-japanese-llama-3.1-8b-instruct",
            "description": "ELYZA Japanese Llama 3.1 8B Instruct (日本語特化)"
        }
    }
    
    print("=== モデルダウンロードスクリプト ===")
    print("ダウンロードしたいモデルを選択してください:")
    
    for key, model in models.items():
        print(f"{key}. {model['description']}")
    
    choice = input("\n選択 (1-2): ").strip()
    
    if choice not in models:
        print("❌ 無効な選択です")
        return
    
    selected_model = models[choice]
    
    # 確認
    print(f"\n選択されたモデル: {selected_model['description']}")
    print(f"ダウンロード先: {selected_model['local_path']}")
    print("⚠️  注意: モデルのダウンロードには時間がかかり、大量のディスク容量が必要です")
    
    confirm = input("ダウンロードを開始しますか? (y/N): ").strip().lower()
    if confirm != 'y':
        print("キャンセルしました")
        return
    
    # ダウンロード実行
    success = download_model(selected_model['name'], selected_model['local_path'])
    
    if success:
        print(f"\n✅ ダウンロード完了!")
        print(f"環境変数を設定してください:")
        print(f"export MODEL_PATH='{selected_model['local_path']}'")
        print(f"export BACKEND_MODE='real'")
    else:
        print("\n❌ ダウンロードに失敗しました")

if __name__ == "__main__":
    main() 