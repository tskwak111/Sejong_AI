import { expect, test, type Page } from "@playwright/test";

/**
 * 이음센터 fixture 모드 - UI 개발·상태 확인 도구 (Q-PM-DEMO-001).
 * fixture 데이터는 전부 MOCK(시연용 샘플)이며 승인·반려 판정과 ACTIVE 전환은
 * 지원하지 않는다. 실패 질문 → 후보 → 별도 승인자 → ACTIVE 전체 완주는
 * actual 전용이므로 admin-core-loop.actual.spec.ts에서만 검증한다.
 *
 * 이 파일은 다음 5가지만 검증한다:
 *  ① "시연용 샘플 — 공식 데이터 아님" 배너 표시
 *  ② 후보 data_origin이 MOCK (시연용 샘플 표기)
 *  ③ 승인/반려(판정) 기능 비활성
 *  ④ ACTIVE 전환 불가
 *  ⑤ 개인정보·브라우저 저장소 미사용
 *
 * ADMIN_UI_MODE=fixture 전제(playwright.config.ts) - 인메모리 admin transport라
 * 127.0.0.1:8000 백엔드를 호출하지 않는다.
 */

function visible(page: Page, role: "button" | "combobox", name?: string) {
  const locator = name
    ? page.getByRole(role, { name })
    : page.getByRole(role);
  return locator.filter({ visible: true }).first();
}

/** 근거 부족 실패 → 사유 확정 → KB 후보 생성 → 승인 화면 진입 (판정 직전까지) */
async function seedCandidateAndOpenReview(page: Page) {
  await page.goto("/admin/failures");
  await expect(page.getByRole("heading", { name: "답변 실패 질문 관리" })).toBeVisible();

  // 큐레이션된 근거 부족 실패 건 (침대 2인용 프레임 수수료 - Q-PM-DEMO-001)
  const curatedRow = () =>
    page
      .locator("article, tr")
      .filter({ hasText: "침대 2인용 프레임은 배출 수수료가 얼마인가요?" })
      .filter({ visible: true })
      .first();
  await expect(curatedRow()).toBeVisible();

  await curatedRow().getByRole("button", { name: "사유 확정" }).click();
  await expect(page.getByText("사유가 확정되었습니다")).toBeVisible();

  await curatedRow().getByRole("button", { name: "KB 후보 생성" }).click();
  await expect(
    page.getByText(/KB 후보 초안이 생성되었습니다/).filter({ visible: true }).first(),
  ).toBeVisible();

  await page.getByRole("link", { name: "KB 후보 승인으로 이동" }).click();
  await expect(page.getByRole("heading", { name: "KB 후보 승인" })).toBeVisible();
}

test("fixture keeps the sample banner and shows MOCK candidates that cannot reach ACTIVE", async ({ page }) => {
  await seedCandidateAndOpenReview(page);

  // ① 시연용 샘플 배너 - 전 화면 상시 노출 (앰버 톤)
  await expect(
    page.getByText("시연용 샘플 — 공식 데이터 아님").first(),
  ).toBeVisible();

  // ② 후보 data_origin=MOCK - 상세 헤더·대기 목록의 "시연용 샘플" 칩.
  //    exact 매칭으로 배너("시연용 샘플 — 공식 데이터 아님")·사이드바
  //    ("시연용 샘플 데이터")와 구분해 MOCK 표기 자체를 확인한다.
  await expect(
    page.getByText("시연용 샘플", { exact: true }).filter({ visible: true }).first(),
  ).toBeVisible();

  // 시연 역할을 별도 승인자로 전환 (인증 아님) - 판정 UI 노출 조건
  await visible(page, "combobox").selectOption("APPROVER");

  // ③ 승인·반려 판정 비활성 + 사유 안내
  const approve = page.getByRole("button", { name: "승인하고 ACTIVE 반영" });
  const reject = page.getByRole("button", { name: "반려" });
  await expect(approve).toBeVisible();
  await expect(approve).toBeDisabled();
  await expect(reject).toBeDisabled();
  await expect(
    page.getByRole("textbox", { name: "검수 의견 (필수)" }),
  ).toBeDisabled();
  await expect(
    page.getByText(/승인·반려 판정을 지원하지 않습니다/),
  ).toBeVisible();

  // ④ ACTIVE 전환 불가 - 검수 의견 입력란까지 잠겨 있어(③) 판정을 진행할 수
  //    없고, 승인 성공 신호(ACTIVE 반영 토스트)는 나타나지 않는다.
  await expect(approve).toBeDisabled();
  await expect(page.getByText("KB 문서가 ACTIVE로 반영되었습니다")).toHaveCount(0);

  // ⑤ 개인정보·저장 정책 - 가로 스크롤 0건, 쿠키·브라우저 저장소 미사용
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

test("purged rows render safely and stored reasons exclude OUT_OF_SCOPE", async ({ page }) => {
  await page.goto("/admin/failures");

  // 30일 파기 행 - NULL이어도 깨지지 않게 렌더링 (CLAUDE.md §6)
  await expect(
    page.getByText(/보관 기간 경과/).filter({ visible: true }).first(),
  ).toBeVisible();

  // 저장 사유 필터는 3종 + 전체 (OUT_OF_SCOPE는 저장되지 않는다).
  // Q-MVP-002/D-059: 개인별 조회·법적 판단도 미저장이라 실제 행은 근거 부족만.
  await expect(visible(page, "button", /^전체 /)).toBeVisible();
  await expect(visible(page, "button", /^근거 부족 /)).toBeVisible();
  await expect(visible(page, "button", /^개인별 조회 /)).toBeVisible();
  await expect(visible(page, "button", /^법적 판단 /)).toBeVisible();
  await expect(page.getByRole("button", { name: /범위 밖/ })).toHaveCount(0);
});
