import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { readFile } from "node:fs/promises";

const apiTarget = process.env.DRAWAI_WORKBENCH_API_URL || "http://127.0.0.1:8890";

export default defineConfig({
  plugins: [react(), {
    name: "drawai-template-catalog",
    configureServer(server) {
      server.middlewares.use("/template-catalog.json", async (_req, res, next) => {
        try {
          const catalog = await readFile(new URL("./templates/data/visual-reference-templates.json", import.meta.url));
          res.setHeader("Content-Type", "application/json; charset=utf-8");
          res.end(catalog);
        } catch (error) { next(error as Error); }
      });
    },
  }],
  optimizeDeps: { entries: ["index.html", "templates.html"] },
  build: {
    rolldownOptions: { input: ["index.html", "templates.html"] },
  },
  server: {
    watch: process.env.DRAWAI_WORKBENCH_POLLING === '1' ? { usePolling: true, interval: 250 } : undefined,
    allowedHosts: ["drawai.yanrupeng.cn"],
    proxy: {
      "/api": apiTarget
    }
  }
});
