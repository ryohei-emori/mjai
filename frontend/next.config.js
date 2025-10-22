const path = require('path')

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Static export設定
  output: 'export',
  trailingSlash: true,
  
  // 静的エクスポート用の画像設定
  images: {
    unoptimized: true
  },

  // 環境変数設定
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  },

  // Webpack設定でパス解決を改善
  webpack: (config) => {
    config.resolve.alias = {
      ...config.resolve.alias,
      '@': path.resolve(__dirname, 'src'),
    }
    return config
  },
}

module.exports = nextConfig
