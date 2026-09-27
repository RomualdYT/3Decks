import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL(".", import.meta.url));

export default defineConfig({
  root,
  publicDir: resolve(root, "public"),
  plugins: [tailwindcss(), react()],
  server: {
    host: "127.0.0.1",
    port: 4173,
    strictPort: true,
    proxy: { "/api": "http://127.0.0.1:38124" },
  },
  build: {
    outDir: resolve(root, "dist"),
    emptyOutDir: true,
    sourcemap: true,
  },
});
