/** @type {import('next').NextConfig} */

const nextConfig = {
  output: 'export',
  distDir: '../public',
  env: {
    name: 'Bootyhole',
    description: 'Bootyhole: a small private-use Kasm workspace registry (generic workspace definitions only).',
    icon: 'https://daledibbadel.github.io/booythole/favicon.ico',
    listUrl: 'https://daledibbadel.github.io/booythole/',
    contactUrl: 'https://github.com/DaleDibbadel/booythole/issues',
  },
  reactStrictMode: true,
  basePath: '/booythole/1.1',
  trailingSlash: true,
  images: {
    unoptimized: true,
  }
}

module.exports = nextConfig
