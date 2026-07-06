/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  base: "/",
  test: {
    environment: "jsdom",
    globals: true,
  },
  server: {
    port: 5173,
    proxy: {
      // Dev convenience: proxy API calls to the FastAPI backend so cookies/SSE
      // work same-origin. Override with VITE_API_URL for a remote backend.
      "/api": {
        target: process.env.VITE_API_URL || "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
