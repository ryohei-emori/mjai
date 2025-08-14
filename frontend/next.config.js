const path = require('path');
const fs = require('fs');

// conf/.envから環境変数を直接読み込み（Dockerコンテナ内のパス）
const envPath = '/app/.env';
let envVars = {};

console.log('=== Next.js Config Debug ===');
console.log('Env file path:', envPath);
console.log('Env file exists:', fs.existsSync(envPath));

if (fs.existsSync(envPath)) {
  const envContent = fs.readFileSync(envPath, 'utf8');
  console.log('Raw env content:', envContent);
  
  envContent.split('\n').forEach(line => {
    const trimmedLine = line.trim();
    if (trimmedLine && !trimmedLine.startsWith('#')) {
      const [key, ...valueParts] = trimmedLine.split('=');
      if (key && valueParts.length > 0) {
        envVars[key] = valueParts.join('=');
        console.log(`Parsed env var: ${key} = ${envVars[key]}`);
      }
    }
  });
  console.log('Final envVars object:', envVars);
} else {
  console.log('Env file not found!');
}

console.log('===========================');

// プレースホルダー判定
function isPlaceholder(value) {
  if (!value) return true;
  const v = String(value).trim();
  return v === 'your_supabase_url_here' || v === 'your_supabase_anon_key_here';
}

function pickEnv(key, fallback) {
  const fromProcess = process.env[key];
  if (fromProcess && !isPlaceholder(fromProcess)) return fromProcess;
  const fromFile = envVars[key];
  if (fromFile && !isPlaceholder(fromFile)) return fromFile;
  return fallback;
}

// 環境変数からngrok URLを取得してCORS設定を動的に生成
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
  
  // 現在のngrokドメインも追加（動的に取得）
  const currentNgrokDomains = [
    '07a9b709a9c2.ngrok-free.app',  // 現在のドメイン
    '67187e4ffba9.ngrok-free.app',  // バックエンドドメイン
    'f82ca07d3e95.ngrok-free.app',  // フロントエンドドメイン
  ];
  
  currentNgrokDomains.forEach(domain => {
    if (!origins.includes(domain)) {
      origins.push(domain);
      console.log(`Added current ngrok domain to CORS: ${domain}`);
    }
  });
  
  console.log('Final CORS origins:', origins);
  return origins;
}

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Fly.io対応の設定
  output: 'standalone',
  
  // 環境変数設定 - クライアントサイドでも利用可能
  env: {
    // バックエンドAPIのベースURL
    BACKEND_NGROK_URL: pickEnv('BACKEND_NGROK_URL', 'http://localhost:8000'),
    FRONTEND_NGROK_URL: pickEnv('FRONTEND_NGROK_URL', 'http://localhost:3000'),
    NEXT_PUBLIC_API_BASE_URL:
      pickEnv('NEXT_PUBLIC_API_BASE_URL') ||
      pickEnv('BACKEND_NGROK_URL', 'http://localhost:8000'),
    NEXT_PUBLIC_BACKEND_NGROK_URL:
      pickEnv('NEXT_PUBLIC_BACKEND_NGROK_URL') ||
      pickEnv('BACKEND_NGROK_URL', 'http://localhost:8000'),
    // Supabase 公開変数
    NEXT_PUBLIC_SUPABASE_URL: pickEnv('NEXT_PUBLIC_SUPABASE_URL'),
    NEXT_PUBLIC_SUPABASE_ANON_KEY: pickEnv('NEXT_PUBLIC_SUPABASE_ANON_KEY'),
  },
  
  // 開発環境でのCORS設定 - 環境変数から動的に生成
  allowedDevOrigins: getCorsOrigins(),
  
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
