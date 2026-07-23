import { expect, test, type Page } from "@playwright/test";

/**
 * ⚠️ actual 전용 스펙 - local API(127.0.0.1:8000) + local Supabase/Postgres
 *    기동 환경에서만 실행한다.
 *
 * 실행 조건 (playwright.config.ts):
 *  - E2E_ACTUAL=1 일 때만 수집·실행된다. GitHub Frontend CI(fixture 기본 경로)
 *    에서는 파일명 필터(**\/*.actual.spec.ts)로 수집조차 되지 않는다.
 *  - webServer는 ADMIN_UI_MODE=actual·CHAT_UI_MODE=actual 로 기동되어 typed
 *    actual admin transport가 same-origin /api/v1/*(Next rewrite →
 *    API_INTERNAL_BASE_URL=127.0.0.1:8000)를 호출한다.
 *
 * 선행 데이터 조건 (operator 책임):
 *  - DB에 INSUFFICIENT_GROUNDING 실패 질문이 최소 1건, 사유 확정 전(NEW)으로
 *    시드되어 있어야 한다. Q-MVP-002/D-059 이후 저장되는 실패 사유는 근거
 *    부족뿐이므로, 큐의 NEW 행은 모두 근거 부족이다.
 *
 * 검증: 실패 질문 큐(NEW) → 사유 확정 → KB 후보 생성 → 승인 화면 →
 *       역할 전환(별도 승인자) → 검수 의견 → OFFICIAL 초안 ACTIVE 승인.
 */

function visible(page: Page, role: "button" | "combobox", name?: string) {
  const locator = name
    ? page.getByRole(role, { name })
    : page.getByRole(role);
  return locator.filter({ visible: true }).first();
}

test("actual local API completes the failure-to-ACTIVE loop with separated roles", async ({ page }) => {
  await page.goto("/admin/failures");
  await expect(page.getByRole("heading", { name: "답변 실패 질문 관리" })).toBeVisible();

  // NEW 근거 부족 행(사유 확정 버튼이 있는 행) 중 보이는 첫 행에서 흐름을 시작한다.
  const actionableRow = page
    .locator("article, tr")
    .filter({ has: page.getByRole("button", { name: "사유 확정" }) })
    .filter({ visible: true })
    .first();
  await expect(
    actionableRow,
    "actual DB에 NEW 근거 부족 실패 질문이 시드되어야 한다",
  ).toBeVisible();

  // 1) 사유 확정 (작성 운영자)
  await actionableRow.getByRole("button", { name: "사유 확정" }).click();
  await expect(page.getByText("사유가 확정되었습니다")).toBeVisible();

  // 2) KB 후보 생성 (근거 부족 + 텍스트 보관 행)
  await actionableRow.getByRole("button", { name: "KB 후보 생성" }).click();
  await expect(
    page.getByText(/KB 후보 초안이 생성되었습니다/).filter({ visible: true }).first(),
  ).toBeVisible();

  // 3) 승인 화면으로 전환
  await page.getByRole("link", { name: "KB 후보 승인으로 이동" }).click();
  await expect(page.getByRole("heading", { name: "KB 후보 승인" })).toBeVisible();

  // 작성 운영자 역할에서는 판정 불가 안내
  await expect(page.getByText(/별도 승인자\(APPROVER\)/)).toBeVisible();

  // 4) 시연 역할 전환 - 인증 아님
  await visible(page, "combobox").selectOption("APPROVER");

  // 5) 검수 의견 필수 - 없으면 승인 비활성
  const approve = page.getByRole("button", { name: "승인하고 ACTIVE 반영" });
  await expect(approve).toBeDisabled();
  await page
    .getByRole("textbox", { name: "검수 의견 (필수)" })
    .fill("공식 출처 원문 대조 완료");
  await expect(approve).toBeEnabled();

  // 6) 승인 → ACTIVE 완료형 + 스탬프
  await approve.click();
  await expect(page.getByText("KB 문서가 ACTIVE로 반영되었습니다")).toBeVisible();
  await expect(page.getByText("다음 시민 답변부터 사용됩니다.")).toBeVisible();

  // 개인정보·저장 정책 - 가로 스크롤 0건, 쿠키·브라우저 저장소 미사용
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
    ),
  ).toBe(true);
  expect(await page.context().cookies()).toEqual([]);
  expect(
    await page.evaluate(() => ({
      localStorageCount: localStorage.length,
      sessionStorageCount: sessionStorage.length,
    })),
  ).toEqual({ localStorageCount: 0, sessionStorageCount: 0 });
});
