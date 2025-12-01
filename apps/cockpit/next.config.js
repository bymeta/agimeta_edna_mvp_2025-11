/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  env: {
    API_GATEWAY_URL: process.env.API_GATEWAY_URL || 'http://localhost:8000',
  },
}

module.exports = nextConfig

