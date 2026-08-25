/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  reactStrictMode: true,
  images: {
    domains: ["localhost"],
  },
  // Draft/review/chat LLM calls often exceed the default 30s rewrite proxy timeout.
  experimental: {
    proxyTimeout: 600000,
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          {
            key: "Content-Security-Policy",
            value:
              "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self' http://localhost:4000 http://127.0.0.1:1234; frame-ancestors 'none'",
          },
        ],
      },
    ];
  },
  async rewrites() {
    const backend =
      process.env.BACKEND_INTERNAL_URL || "http://localhost:4000/api/v1";
    return [
      {
        source: "/api/v1/:path*",
        destination: `${backend.replace(/\/$/, "")}/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
