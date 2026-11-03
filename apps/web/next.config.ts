import path from "node:path";
import type { NextConfig } from "next";

const securityHeaders = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
];

const nextConfig: NextConfig = {
  output: "standalone",
  // Separate build folders let a QA/production build run beside a `next dev` session without clobbering it.
  distDir: process.env.NEXT_DIST_DIR || ".next",
  // Trace workspace packages from the monorepo root so the standalone bundle includes them.
  outputFileTracingRoot: path.join(import.meta.dirname, "../.."),
  transpilePackages: ["@commerce-os/api-client", "@commerce-os/design-system"],
  poweredByHeader: false,
  reactStrictMode: true,
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
};

export default nextConfig;
