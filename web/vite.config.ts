import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The Python server runs on :8000; the dev server forwards /api to it.
export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": "http://localhost:8000" } },
});
