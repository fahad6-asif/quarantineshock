import { defineConfig, devices } from "@playwright/test";

// The demo path runs in replay mode (cache only, zero network). Run `python scripts/warm_cache.py` once first.
export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 180_000,
  expect: { timeout: 30_000 },
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  use: {
    ...devices["Desktop Chrome"],
    baseURL: process.env.E2E_BASE_URL || "http://localhost:3000",
    viewport: { width: 1366, height: 768 }, // the laptop size from the spec (after the preset, so it wins)
    trace: "retain-on-failure",
  },
  webServer: process.env.E2E_BASE_URL ? undefined : [
    {
      command: "node ../scripts/run-api.mjs",
      url: "http://localhost:8000/api/health",
      reuseExistingServer: true,
      env: { LLM_PROVIDER: "replay" },
      timeout: 120_000,
    },
    { command: "npm run dev", url: "http://localhost:3000", reuseExistingServer: true, timeout: 120_000 },
  ],
});
