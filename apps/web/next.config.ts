import type { NextConfig } from "next";

const localApiBaseUrl = process.env.API_INTERNAL_BASE_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  // Development-only Next.js assets and HMR may be requested through the documented loopback host.
  allowedDevOrigins: ["127.0.0.1"],
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${localApiBaseUrl}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
