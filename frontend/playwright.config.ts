/**
 * Playwright smoke tests (Phase 6 hardening): the critical paths that must
 * never break silently - the board renders, the mode banner tells the truth,
 * and the kill switch fires end-to-end.
 *
 * The API runs against a SCRATCH ledger root (e2e-data/), never data/: the
 * kill-switch test really fires a kill, and a kill in the real append-only
 * ledger would stick until a CLI re-arm exists.
 */
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  retries: 0,
  use: {
    baseURL: "http://127.0.0.1:3000",
  },
  webServer: [
    {
      // Scratch-root API on 8001; fresh ledger per run.
      command:
        "rm -rf ../e2e-data && mkdir -p ../e2e-data/data/ledger ../e2e-data/data/runs && " +
        "cd .. && WC2026_ROOT=$(pwd)/e2e-data uv run uvicorn wc2026.api.server:app --host 127.0.0.1 --port 8001",
      url: "http://127.0.0.1:8001/api/v1/health",
      reuseExistingServer: false,
      timeout: 60_000,
    },
    {
      // Vite dev pointed at the scratch API. Must be port 3000: the API's
      // CORS allowlist is deliberately exact (ADR-0011).
      command: "VITE_API_URL=http://127.0.0.1:8001 npm run dev -- --port 3000 --strictPort",
      url: "http://127.0.0.1:3000",
      reuseExistingServer: false,
      timeout: 60_000,
    },
  ],
});
