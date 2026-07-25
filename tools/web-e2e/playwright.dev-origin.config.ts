import { defineConfig } from "@playwright/test";

const corepack = process.platform === "win32" ? "corepack.cmd" : "corepack";

export default defineConfig({
  testDir: "./e2e",
  testMatch: "dev-origin.spec.ts",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: "http://localhost:3002",
    browserName: "chromium",
    viewport: { width: 1440, height: 900 },
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  webServer: {
    command:
      `${corepack} pnpm --filter @sejong-ai/web exec next dev --hostname localhost --port 3002`,
    cwd: "../..",
    url: "http://localhost:3002",
    reuseExistingServer: false,
    timeout: 120_000,
  },
});
