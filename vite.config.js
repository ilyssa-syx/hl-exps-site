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

function htmlInputsBelow(directory, prefix) {
  if (!fs.existsSync(directory)) return {};
  const inputs = {};
  const visit = (current) => {
    for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
      const child = path.join(current, entry.name);
      if (entry.isDirectory()) visit(child);
      if (entry.isFile() && entry.name === "index.html") {
        const relative = path.relative(directory, child).replaceAll(path.sep, "-");
        inputs[`${prefix}-${relative}`] = child;
      }
    }
  };
  visit(directory);
  return inputs;
}

const experimentInputs = htmlInputsBelow(path.join(root, "experiments"), "experiment");

export default defineConfig({
  base: "/hl-exps-site/",
  define: {
    __BUILD_ID__: JSON.stringify(process.env.GITHUB_SHA ?? "dev"),
  },
  build: {
    target: "es2022",
    sourcemap: true,
    rollupOptions: {
      input: {
        index: path.join(root, "index.html"),
        ...sampleInputs,
        ...experimentInputs,
      },
    },
  },
});
