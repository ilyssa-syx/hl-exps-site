import { defineConfig } from "vite";

export default defineConfig({
  base: "/hl-exps-site/",
  build: {
    target: "es2022",
    sourcemap: true,
  },
});
