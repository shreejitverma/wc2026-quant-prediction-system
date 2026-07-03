import path from "node:path";
import { defineConfig } from "vitest/config";

// No @vitejs/plugin-react: vitest 4 transforms TSX with the automatic JSX
// runtime out of the box, which is all component tests need (no fast refresh).
export default defineConfig({
  resolve: { alias: { "@": path.resolve(__dirname, "src") } },
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
