import { setWorkerUrl } from "maplibre-gl";

// Must run before the first map is created. The file is copied by scripts/copy-maplibre-worker.mjs.
if (typeof window !== "undefined") setWorkerUrl("/maplibre-gl-worker.mjs");
