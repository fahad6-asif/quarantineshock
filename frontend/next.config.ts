import type { NextConfig } from "next";

// STATIC_EXPORT=1 builds plain HTML/JS into out/ so the FastAPI server can host the whole app from one
// address (used for the public deployment, see Dockerfile). Local `npm run dev` is unaffected.
const staticExport = !!process.env.STATIC_EXPORT;

const nextConfig: NextConfig = {
  devIndicators: false, // no floating dev button during demos
  ...(staticExport ? { output: "export", trailingSlash: true } : { cacheComponents: true, partialPrefetching: true }),
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
