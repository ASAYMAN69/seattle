import { defineConfig } from "vite";

/**
 * Dev proxy (contract with the FastAPI service, built in parallel by the
 * Wizard agent): during `vite` development, API calls go to
 * `http://localhost:8000`. In production, the FastAPI service serves
 * `web/dist/` statically, so the SPA talks to `/api/...` same-origin.
 *
 * To run the SPA without the backend yet, use `npm run dev:mock`, which starts
 * a small dev-only API server on port 8000 (web/scripts/dev-api.mjs) that
 * serves the REAL prepared data from data/prepared/.
 */
export default defineConfig({
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  // `npm start` / `vite preview` serves the production build; keep the same
  // /api proxy so the built SPA talks to the FastAPI backend the same way.
  preview: {
    port: 4173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: true,
  },
});
