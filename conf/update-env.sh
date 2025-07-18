#!/bin/bash

# ngrokのURLを取得する関数
get_ngrok_url() {
    local tunnel_name=$1
    local max_attempts=30
    local attempt=1
    
    echo "Waiting for ngrok tunnel '$tunnel_name' to be ready..." >&2
    
    while [ $attempt -le $max_attempts ]; do
        tunnel_info=$(curl -s http://localhost:4040/api/tunnels | jq -r ".tunnels[] | select(.name == \"$tunnel_name\") | .public_url")
        if [ "$tunnel_info" != "null" ] && [ -n "$tunnel_info" ]; then
            echo "Found $tunnel_name URL: $tunnel_info" >&2
            echo "$tunnel_info"
            return 0
        fi
        echo "Attempt $attempt/$max_attempts: Waiting for $tunnel_name tunnel..." >&2
        sleep 2
        attempt=$((attempt + 1))
    done
    echo "Failed to get $tunnel_name URL after $max_attempts attempts" >&2
    return 1
}

main() {
    echo "Starting environment update script..."
    backend_url=$(get_ngrok_url "backend")
    if [ $? -ne 0 ]; then
        echo "Error: Could not get backend URL"
        exit 1
    fi
    frontend_url=$(get_ngrok_url "frontend")
    if [ $? -ne 0 ]; then
        echo "Error: Could not get frontend URL"
        exit 1
    fi

    # .envファイルが存在しない場合は作成
    if [ ! -f .env ]; then
        echo "Creating .env file..."
        touch .env
    fi

    # ngrokのURLのみを更新（既存の値は保持）
    # 既存の行を更新、存在しない場合は追加
    if grep -q "^BACKEND_NGROK_URL=" .env; then
        sed -i '' "s|^BACKEND_NGROK_URL=.*|BACKEND_NGROK_URL=${backend_url}|" .env
    else
        echo "BACKEND_NGROK_URL=${backend_url}" >> .env
    fi
    
    if grep -q "^FRONTEND_NGROK_URL=" .env; then
        sed -i '' "s|^FRONTEND_NGROK_URL=.*|FRONTEND_NGROK_URL=${frontend_url}|" .env
    else
        echo "FRONTEND_NGROK_URL=${frontend_url}" >> .env
    fi

    # NEXT_PUBLIC_API_BASE_URLもバックエンドURLで上書き
    if grep -q "^NEXT_PUBLIC_API_BASE_URL=" .env; then
        sed -i '' "s|^NEXT_PUBLIC_API_BASE_URL=.*|NEXT_PUBLIC_API_BASE_URL=${backend_url}|" .env
    else
        echo "NEXT_PUBLIC_API_BASE_URL=${backend_url}" >> .env
    fi

    echo "Environment updated (existing values preserved):"
    echo "Backend URL: ${backend_url}"
    echo "Frontend URL: ${frontend_url}"

    # --no-docker オプションがなければfrontendを再起動
    if [[ "$1" != "--no-docker" ]]; then
        if command -v docker-compose &> /dev/null; then
            echo "Updating frontend container environment..."
            docker-compose stop frontend
            docker-compose up -d frontend
        fi
    fi
}

main "$@" 