import path from "node:path";
import react from "@vitejs/plugin-react-swc";
import { defineConfig } from "vitest/config";

// One config for dev server, build, and tests (ADR-0015): a solo maintainer
// should have exactly one place where aliases and transforms are defined.
export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": path.resolve(__dirname, "src") } },
  server: {
    port: 3000,
    // Terminal is localhost-only, same as the API (ADR-0011).
    host: "127.0.0.1",
  },
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
