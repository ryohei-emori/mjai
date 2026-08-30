const path = require('path')

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Static export for Vercel monorepo deployment (frontend in subdirectory)
  output: 'export',
  trailingSlash: true,

  // Disable Next.js dev indicators (floating badge) in all environments
  devIndicators: false,

  // Vercel's Image Optimization is available, but keeping unoptimized: true
  // until next/image usage is reviewed. Flip to false as a follow-up to
  // enable Vercel's native image optimization.
  images: {
    unoptimized: true
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
