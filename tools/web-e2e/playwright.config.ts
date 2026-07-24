import { defineConfig } from "@playwright/test";

const corepack = process.platform === "win32" ? "corepack.cmd" : "corepack";

/**
 * 실행 모드 분리 (태성 CI 교정):
 * - 기본(GitHub Frontend CI): fixture 프로젝트만 수집한다. 이음센터는
 *   ADMIN_UI_MODE=fixture 인메모리 transport라 127.0.0.1:8000 백엔드를
 *   호출하지 않는다. 시민 대화 스펙은 page.route로 /api/v1/chat을 브라우저
 *   단계에서 가로채므로 CHAT_UI_MODE=actual 이라도 실제 백엔드에 도달하지
 *   않는다. actual 전용 스펙(**\/*.actual.spec.ts)은 수집조차 되지 않는다.
 * - actual(E2E_ACTUAL=1): local API + local DB 기동 환경 전용. actual 스펙만
 *   수집하고 ADMIN_UI_MODE=actual 로 실제 admin transport를 사용한다.
 * 두 모드는 상호 배타적이다(env가 프로세스 전역이므로 한 실행에 하나의 모드).
 */
const runActual = process.env.E2E_ACTUAL === "1";

const viewports = [
  { name: "mobile-390", width: 390, height: 844 },
  { name: "mobile-430", width: 430, height: 932 },
  { name: "desktop", width: 1440, height: 900 },
] as const;

const fixtureProjects = viewports.map((v) => ({
  name: v.name,
  use: { viewport: { width: v.width, height: v.height } },
  // 기본 실행에서는 actual 전용 스펙을 수집하지 않는다 (127.0.0.1:8000 미접촉).
  testIgnore: "**/*.actual.spec.ts",
}));

// actual 흐름은 DB를 변형하므로 뷰포트별 중복 실행 대신 desktop 단일 프로젝트로 둔다.
const actualProjects = [
  {
    name: "actual-desktop",
    use: { viewport: { width: 1440, height: 900 } },
    testMatch: "**/*.actual.spec.ts",
  },
];

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: runActual ? 1 : 3,
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
      // 기본 fixture 실행: 이음센터는 인메모리 fixture transport(백엔드 미호출).
      // actual 실행에서만 actual admin transport로 전환한다.
      ADMIN_UI_MODE: runActual ? "actual" : "fixture",
      // 시민 대화 스펙은 page.route로 /api/v1/chat을 가로채므로 fixture 실행에서도
      // actual transport라도 실제 백엔드(127.0.0.1:8000)에 도달하지 않는다.
      CHAT_UI_MODE: "actual",
    },
  },
  projects: runActual ? actualProjects : fixtureProjects,
});
