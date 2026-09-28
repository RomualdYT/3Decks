import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const desktop = fileURLToPath(new URL(".", import.meta.url));
const frontend = resolve(desktop, "frontend");

export default defineConfig({
  root: frontend,
  publicDir: resolve(frontend, "public"),
  plugins: [tailwindcss(), react()],
  define: { "import.meta.env.VITE_DECKS_DESKTOP": JSON.stringify("1") },
  resolve: {
    alias: [
      { find: /^\.\/api\/http$/, replacement: resolve(desktop, "src/tauri-api.ts") },
      { find: /^\.\/app\/App$/, replacement: resolve(desktop, "src/DesktopRoot.tsx") },
    ],
    dedupe: ["react", "react-dom"],
  },
  server: {
    host: "127.0.0.1", port: 4174, strictPort: true,
    fs: { allow: [desktop, resolve(frontend, "..")] },
  },
  build: { outDir: resolve(desktop, "dist"), emptyOutDir: true },
  clearScreen: false,
});
