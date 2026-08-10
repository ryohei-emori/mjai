const path = require('path')

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Static export for Vercel monorepo deployment (frontend in subdirectory)
  output: 'export',
  trailingSlash: true,

  // Vercel's Image Optimization is available, but keeping unoptimized: true
  // until next/image usage is reviewed. Flip to false as a follow-up to
  // enable Vercel's native image optimization.
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
