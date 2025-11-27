/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true, // Enables React strict mode for better error handling
  swcMinify: true,       // Uses SWC for faster minification

  // Enable experimental features if needed (optional)
  // For example, if you want to use the built-in font optimization:
  // experimental: {
  //   appDir: false, // Set to true if you are using the App Router (pages directory is used by default)
  // },

  // Configure image optimization to allow the Raeburn logo from their domain
  images: {
    // Add the domain for the Raeburn Group logo
    // This is necessary if you use the <Image> component with this external URL
    // or if you want to optimize images from this domain.
    domains: ['theraeburngroup-recruitment.com'],
    // You can also configure other image settings here if needed
    // deviceSizes: [640, 750, 828, 1080, 1200, 1920, 2048, 3840],
    // imageSizes: [16, 32, 48, 64, 96, 128, 256, 384],
  },

  // Configure environment variables (optional)
  // This allows you to expose environment variables to the browser
  // Make sure to prefix with NEXT_PUBLIC_ in your .env file
  // env: {
  //   CUSTOM_KEY: process.env.CUSTOM_KEY,
  // },

  // Configure webpack (optional)
  // webpack(config) {
  //   // Perform custom webpack configuration here
  //   return config;
  // },

  // Redirects (optional)
  // async redirects() {
  //   return [
  //     {
  //       source: '/',
  //       destination: '/dashboard',
  //       permanent: false, // Use 307 Temporary Redirect
  //       // or permanent: true for 308 Permanent Redirect
  //     },
  //   ]
  // },

  // Rewrites (optional)
  // async rewrites() {
  //   return [
  //     {
  //       source: '/api/:path*',
  //       destination: `${process.env.API_URL}/:path*` // Proxy to Backend
  //     }
  //   ]
  // }
};

module.exports = nextConfig;
