/** @type {import('next').NextConfig} */
const isProd = process.env.NODE_ENV === 'production'
const isGitHubPages = process.env.GITHUB_PAGES === 'true'

const nextConfig = {
  reactStrictMode: true,
  output: 'export',
  images: {
    unoptimized: true,
  },
  // Only add basePath and assetPrefix for GitHub Pages production builds
  ...(isProd && isGitHubPages && {
    basePath: '/landing_page_RJLF',
    assetPrefix: '/landing_page_RJLF',
  }),
  trailingSlash: true,
}

module.exports = nextConfig