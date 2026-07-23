import { defineConfig } from "@playwright/test";

const corepack = process.platform === "win32" ? "corepack.cmd" : "corepack";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 3,
  forbidOnly: true,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:3001",
    browserName: "chromium",
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  webServer: {
    command:
      `${corepack} pnpm --filter @sejong-ai/web exec next start --hostname 127.0.0.1 --port 3001`,
    cwd: "../..",
    url: "http://127.0.0.1:3001",
    reuseExistingServer: false,
    timeout: 120_000,
    env: {
      ...process.env,
      ADMIN_UI_ENABLED: "true",
      // e2e는 라우트 인터셉션으로 /api/v1/chat을 검증하므로 actual transport 사용
      CHAT_UI_MODE: "actual",
    },
  },
  projects: [
    { name: "mobile-390", use: { viewport: { width: 390, height: 844 } } },
    { name: "mobile-430", use: { viewport: { width: 430, height: 932 } } },
    { name: "desktop", use: { viewport: { width: 1440, height: 900 } } },
  ],
});
