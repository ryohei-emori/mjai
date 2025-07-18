FROM node:18-alpine

WORKDIR /app

# 依存関係のインストール
COPY package*.json ./
RUN npm install

# アプリケーションコードのコピー
COPY . .

# ポートの公開
EXPOSE 3000

# アプリケーションの起動
CMD ["npm", "run", "dev"] 