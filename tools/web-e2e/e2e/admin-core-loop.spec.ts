import { expect, test, type Page } from "@playwright/test";

/**
 * 이음센터 핵심 루프 (데모 #5) - fixture 모드:
 * 실패 질문 큐(NEW) → 사유 확정 → 근거 부족 건 KB 후보 생성 →
 * 승인 화면 이동 → 역할 전환(별도 승인자) → 검수 의견 작성 →
 * 공식 출처(OFFICIAL) 초안 ACTIVE 승인. 브라우저 저장소·쿠키 미사용 유지.
 */

function visible(page: Page, role: "button" | "combobox", name?: string) {
  const locator = name
    ? page.getByRole(role, { name })
    : page.getByRole(role);
  return locator.filter({ visible: true }).first();
}

test("local admin fixture completes the failure-to-ACTIVE loop with separated roles", async ({ page }) => {
  await page.goto("/admin/failures");

  await expect(page.getByRole("heading", { name: "답변 실패 질문 관리" })).toBeVisible();

  // 큐레이션된 근거 부족 실패 건이 신규 상태로 보인다 (모바일 카드/테이블 중 보이는 쪽)
  const curatedRow = () =>
    page
      .locator("article, tr")
      .filter({ hasText: "전입신고를 대리인이 하면 위임장 공증이 필요한가요?" })
      .filter({ visible: true })
      .first();
  await expect(curatedRow()).toBeVisible();

  // 1) 사유 확정 (작성 운영자) - 해당 행에서만
  await curatedRow().getByRole("button", { name: "사유 확정" }).click();
  await expect(page.getByText("사유가 확정되었습니다")).toBeVisible();

  // 2) KB 후보 생성 (근거 부족 + 텍스트 보관 행에만 노출)
  await curatedRow().getByRole("button", { name: "KB 후보 생성" }).click();
  await expect(
    page.getByText(/KB 후보 초안이 생성되었습니다/).filter({ visible: true }).first(),
  ).toBeVisible();

  // 3) 승인 화면으로 전환 (데모 #5의 화면 전환)
  await page.getByRole("link", { name: "KB 후보 승인으로 이동" }).click();
  await expect(page.getByRole("heading", { name: "KB 후보 승인" })).toBeVisible();
  await expect(
    page.getByText("전입신고 대리인 위임 요건").filter({ visible: true }).first(),
  ).toBeVisible();

  // 작성 운영자 역할에서는 판정 불가 안내
  await expect(page.getByText(/별도 승인자\(APPROVER\)/)).toBeVisible();

  // 4) 시연 역할 전환 - 인증 아님
  await visible(page, "combobox").selectOption("APPROVER");

  // 5) 검수 의견 필수 - 없으면 승인 비활성
  const approve = page.getByRole("button", { name: "승인하고 ACTIVE 반영" });
  await expect(approve).toBeDisabled();
  await page
    .getByRole("textbox", { name: "검수 의견 (필수)" })
    .fill("정부24 공식 안내 원문 대조 완료");
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

test("purged rows render safely and stored reasons exclude OUT_OF_SCOPE", async ({ page }) => {
  await page.goto("/admin/failures");

  // 30일 파기 행 - NULL이어도 깨지지 않게 렌더링 (CLAUDE.md §6)
  await expect(
    page.getByText(/보관 기간 경과/).filter({ visible: true }).first(),
  ).toBeVisible();

  // 저장 사유 필터는 3종 + 전체 (OUT_OF_SCOPE는 저장되지 않는다)
  await expect(visible(page, "button", /^전체 /)).toBeVisible();
  await expect(visible(page, "button", /^근거 부족 /)).toBeVisible();
  await expect(visible(page, "button", /^개인별 조회 /)).toBeVisible();
  await expect(visible(page, "button", /^법적 판단 /)).toBeVisible();
  await expect(page.getByRole("button", { name: /범위 밖/ })).toHaveCount(0);
});
