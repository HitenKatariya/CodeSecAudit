/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  // Emit a self-contained server bundle so the Docker runtime only needs the
  // traced files instead of the full node_modules tree (~150-200 MB image).
  output: "standalone",
};

module.exports = nextConfig;
