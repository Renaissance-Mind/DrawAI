import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  base: "./",
  build: {
    outDir: "dist-plugin",
    assetsInlineLimit: 1000000,
    cssCodeSplit: false,
    modulePreload: false,
    rolldownOptions: {
      input: "templates.html",
      output: { codeSplitting: false },
    },
  },
});
