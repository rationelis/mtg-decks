import { defineConfig } from "vite";

// GitHub Pages serves project sites from /<repo-name>/, so the base path
// is set via an env var at CI build time (falls back to "/" for local dev).
export default defineConfig({
  base: process.env.BASE_PATH ?? "/",
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
});
