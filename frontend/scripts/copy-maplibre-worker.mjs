// MapLibre locates its web worker relative to its own module URL, which Turbopack rewrites.
// Serve the standalone worker from /public instead (see src/lib/maplibre.ts).
import { copyFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const src = join(root, "node_modules", "maplibre-gl", "dist", "maplibre-gl-worker.mjs");
const dest = join(root, "public", "maplibre-gl-worker.mjs");
if (existsSync(src)) {
  mkdirSync(dirname(dest), { recursive: true });
  copyFileSync(src, dest);
  console.log("copied maplibre-gl-worker.mjs to public/");
}
