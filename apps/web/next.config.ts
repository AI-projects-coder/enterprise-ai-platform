import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Standalone output is what the production Docker image (Dockerfile.prod)
  // runs from — a self-contained server.js with only the deps actually
  // used, instead of shipping the full node_modules tree. Doesn't affect
  // `next dev` at all, only `next build`.
  output: "standalone",
};

export default nextConfig;
