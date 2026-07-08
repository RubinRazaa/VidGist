const BACKEND = process.env.BACKEND_URL || "http://127.0.0.1:8000";

const nextConfig = {
  // Video analysis (download + Gemini video processing) can take ~45-90s.
  // The dev rewrite proxy defaults to a 30s timeout, which cut requests off
  // and surfaced as "Can't reach the backend" in the UI. Give it room.
  experimental: {
    proxyTimeout: 120_000,
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${BACKEND}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
