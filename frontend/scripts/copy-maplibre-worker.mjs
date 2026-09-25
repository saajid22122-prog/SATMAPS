// Copies MapLibre GL JS v6's real worker files (maplibre-gl-worker.mjs +
// its sibling maplibre-gl-shared.mjs) into public/ so they're servable at a
// stable same-origin URL. Necessary because Turbopack does not correctly
// resolve the worker's own relative module path inside the bundle - see
// the comment in src/components/MapView.tsx next to setWorkerUrl().
import { copyFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const srcDir = join(__dirname, "..", "node_modules", "maplibre-gl", "dist");
const outDir = join(__dirname, "..", "public", "maplibre-worker");

mkdirSync(outDir, { recursive: true });
for (const file of ["maplibre-gl-worker.mjs", "maplibre-gl-shared.mjs"]) {
  copyFileSync(join(srcDir, file), join(outDir, file));
}
console.log("Copied MapLibre worker files to public/maplibre-worker/");
