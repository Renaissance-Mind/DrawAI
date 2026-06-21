import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const apiTarget = process.env.DRAWAI_WORKBENCH_API_URL || "http://127.0.0.1:8890";

export default defineConfig({
  plugins: [react()],
  server: {
    allowedHosts: ["drawai.yanrupeng.cn"],
    proxy: {
      "/api": apiTarget
    }
  }
});
