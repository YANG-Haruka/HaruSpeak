/** @type {import('next').NextConfig} */
const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8000";

// In dev (`next dev`) we proxy /api and /ws to the FastAPI backend.
// In `next build` for the frozen app (BUILD_TARGET=export), we emit a static
// `out/` bundle that FastAPI serves directly — same origin, no proxy needed.
const isStaticExport = process.env.BUILD_TARGET === "export";

const nextConfig = isStaticExport
  ? {
      reactStrictMode: true,
      output: "export",
      // Each page exports as `<route>/index.html` — FastAPI's StaticFiles
      // (html=True) auto-finds index.html, so /settings/ works out of the box.
      // Without this, Next.js emits flat `settings.html` and FastAPI 404s
      // on /settings (only / falls back to index.html).
      trailingSlash: true,
      images: { unoptimized: true },
    }
  : {
      reactStrictMode: true,
      async rewrites() {
        return [
          { source: "/api/:path*", destination: `${BACKEND}/api/:path*` },
          { source: "/ws/:path*",  destination: `${BACKEND}/ws/:path*` },
          { source: "/healthz",    destination: `${BACKEND}/healthz` },
        ];
      },
    };

module.exports = nextConfig;
