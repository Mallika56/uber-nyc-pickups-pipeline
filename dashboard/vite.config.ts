import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In development the API runs separately on :8000; proxy its routes so the app can use
// relative URLs. In production FastAPI serves the built files itself, same origin.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000",
    },
  },
});
