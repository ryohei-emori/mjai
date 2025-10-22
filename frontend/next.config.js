const path = require('path');
const fs = require('fs');

// conf/.envから環境変数を直接読み込み（Dockerコンテナ内のパス）
let envVars = {};

// Helper to pick env vars with fallback
function pickEnv(key, fallback) {
  const value = process.env[key];
  return value || fallback;
}

// Configure CORS origins for development/production
function getCorsOrigins() {
  const origins = [
    '192.168.0.34',
    'localhost',
    '127.0.0.1',
    '172.22.178.95',
    '0.0.0.0',
    // ngrok domains
    'ngrok-free.app',
    'ngrok.io',
    'ngrok.app',
  ];
  
  // 環境変数からngrok URLを取得してドメイン部分を抽出
  const frontendNgrokUrl = pickEnv('FRONTEND_NGROK_URL');
  const backendNgrokUrl = pickEnv('BACKEND_NGROK_URL');
  
  if (frontendNgrokUrl) {
    try {
      const frontendDomain = new URL(frontendNgrokUrl).hostname;
      origins.push(frontendDomain);
      console.log(`Added frontend ngrok domain to CORS: ${frontendDomain}`);
    } catch (e) {
      console.warn('Invalid frontend ngrok URL:', frontendNgrokUrl);
    }
  }
  
  if (backendNgrokUrl) {
    try {
      const backendDomain = new URL(backendNgrokUrl).hostname;
      origins.push(backendDomain);
      console.log(`Added backend ngrok domain to CORS: ${backendDomain}`);
    } catch (e) {
      console.warn('Invalid backend ngrok URL:', backendNgrokUrl);
    }
  }
  
  console.log('Final CORS origins:', origins);
  return origins;
}

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Render対応の設定
  output: 'standalone',
  
  // 環境変数設定 - クライアントサイドでも利用可能
  env: {
    // バックエンドAPIのベースURL
    NEXT_PUBLIC_API_URL: pickEnv('NEXT_PUBLIC_API_URL', 'http://localhost:8000'),
  },
  
  // CORS設定 - セキュリティのため本番ではRenderドメインのみ許可
  allowedDevOrigins: [
    'localhost',
    '127.0.0.1',
    'onrender.com', // Render domains
  ],
  
  // Turbopack設定（experimental.turboは非推奨）
  turbopack: {
    rules: {
      '*.svg': {
        loaders: ['@svgr/webpack'],
        as: '*.js',
      },
    },
  },
  
  // 画像最適化設定
  images: {
    domains: ['localhost', '127.0.0.1', 'ngrok-free.app', 'ngrok.io', 'ngrok.app'],
  },
}

console.log('Final nextConfig.env:', nextConfig.env);

module.exports = nextConfig
