/** @type {import('next').NextConfig} */
const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8000";

const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    // Proxy HTTP API + WebSocket through this origin so everything works
    // behind a single HTTPS tunnel (cloudflared, ngrok, etc.) on mobile.
    return [
      { source: "/api/:path*",   destination: `${BACKEND}/api/:path*` },
      { source: "/ws/:path*",    destination: `${BACKEND}/ws/:path*` },
      { source: "/healthz",      destination: `${BACKEND}/healthz` },
    ];
  },
};

module.exports = nextConfig;
