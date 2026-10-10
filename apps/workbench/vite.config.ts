import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const apiTarget = process.env.DRAWAI_WORKBENCH_API_URL || "http://127.0.0.1:8890";

export default defineConfig({
  plugins: [react()],
  optimizeDeps: { entries: ["index.html", "studio.html"] },
  build: {
    rolldownOptions: { input: ["index.html", "studio.html"] },
  },
  server: {
    watch: process.env.DRAWAI_WORKBENCH_POLLING === '1' ? { usePolling: true, interval: 250 } : undefined,
    allowedHosts: ["drawai.yanrupeng.cn"],
    proxy: {
      "/api/studio": process.env.DRAWAI_STUDIO_API_URL || "http://127.0.0.1:8896",
      "/api": apiTarget
    }
  }
});
