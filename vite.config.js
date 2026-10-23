import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";

const root = path.dirname(fileURLToPath(import.meta.url));
const samplesRoot = path.join(root, "samples");
const sampleInputs = fs.existsSync(samplesRoot)
  ? Object.fromEntries(
      fs.readdirSync(samplesRoot, { withFileTypes: true })
        .filter((entry) => entry.isDirectory())
        .map((entry) => [
          `sample-${entry.name}`,
          path.join(samplesRoot, entry.name, "index.html"),
        ]),
    )
  : {};

export default defineConfig({
  base: "/hl-exps-site/",
  build: {
    target: "es2022",
    sourcemap: true,
    rollupOptions: {
      input: {
        index: path.join(root, "index.html"),
        ...sampleInputs,
      },
    },
  },
});
