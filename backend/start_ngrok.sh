#!/bin/bash

# conf/.envから環境変数を読み込み
if [ -f "../conf/.env" ]; then
    export $(cat ../conf/.env | grep -v '^#' | xargs)
    echo "Loaded environment variables from conf/.env"
else
    echo "Warning: conf/.env not found"
fi

# ngrok authtokenを設定
if [ ! -z "$NGROK_AUTHTOKEN" ]; then
    ngrok config add-authtoken $NGROK_AUTHTOKEN
    echo "ngrok authtoken configured"
else
    echo "Warning: NGROK_AUTHTOKEN not set in conf/.env"
fi

# ngrokを起動
echo "Starting ngrok tunnel for port 8000..."
ngrok http 8000 --log=stdout 