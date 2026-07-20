import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  distDir: "dist",
  images: { unoptimized: true },
  reactStrictMode: true,
};

export default nextConfig;
