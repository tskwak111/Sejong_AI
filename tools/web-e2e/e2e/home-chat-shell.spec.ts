import { expect, test, type Page } from "@playwright/test";

const successResponse = {
  request_id: "11111111-1111-4111-8111-111111111111",
  answer_status: "SUCCESS",
  intent: "MOVE_IN_RESIDENT_REGISTRATION",
  confidence: 0.99,
  summary: "전입신고 절차를 공식 근거에서 확인했어요.",
  procedure_steps: ["신고 내용을 확인합니다.", "공식 신청 경로를 이용합니다."],
  required_documents: ["신분증"],
  processing_time: "즉시",
  fee: "무료",
  department: "주민등록 담당",
  sources: [
    {
      source_id: "KB-MOVE-01",
      title: "시연용 샘플 전입신고 공식 안내",
      url: "https://example.invalid/official/move-in",
      last_verified_at: "2026-07-20",
    },
  ],
  office: null,
  followup_options: [],
  fallback: null,
  context_token: "signed-success-context",
};

async function submit(page: Page, question: string) {
  const textbox = page.getByRole("textbox", { name: "질문 입력" });
  const submitButton = page.getByRole("button", { name: "전송" });

  await expect(async () => {
    await textbox.fill(question);
    await expect(textbox).toHaveValue(question, { timeout: 250 });
    await expect(submitButton).toBeEnabled({ timeout: 250 });
  }).toPass({
    timeout: 5_000,
    intervals: [50, 100, 250, 500],
  });

  await submitButton.click();
}

test("home question input reaches chat and renders a grounded source strip", async ({ page }) => {
  await page.route("**/api/v1/chat", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(successResponse) }),
  );
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("궁금한 민원을 물어보세요");

  const homeInput = page.getByRole("textbox", { name: "질문 입력" });
  await homeInput.fill("전입신고 절차를 알려줘");
  await page.getByRole("button", { name: /질문하기/ }).click();

  await expect(page).toHaveURL(/\/chat\?q=/);
  await expect(page.getByText(successResponse.summary)).toBeVisible();
  await expect(page.getByText(successResponse.sources[0].title)).toBeVisible();
  await expect(page.getByText("공식 출처 확인")).toBeVisible();
  await expect(page.getByRole("link", { name: /원문 보기/ })).toHaveAttribute(
    "href",
    successResponse.sources[0].url,
  );
});

test("follow-up uses its signed in-memory context once and stores nothing", async ({ page }) => {
  const requests: Record<string, unknown>[] = [];
  await page.route("**/api/v1/chat", async (route) => {
    const request = route.request().postDataJSON() as Record<string, unknown>;
    requests.push(request);
    const response = requests.length === 1
      ? {
          request_id: "22222222-2222-4222-8222-222222222222",
          answer_status: "FOLLOWUP",
          intent: "UNKNOWN",
          confidence: null,
          summary: null,
          procedure_steps: [],
          required_documents: [],
          processing_time: null,
          fee: null,
          department: null,
          sources: [],
          office: null,
          followup_options: ["전입신고는 언제까지 해야 하나요?", "주민등록등본은 어떻게 발급받나요?"],
          fallback: null,
          context_token: "signed-followup-context",
        }
      : successResponse;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(response) });
  });

  await page.goto("/chat");
  await submit(page, "신고하고 싶어요.");
  const option = page.getByRole("button", { name: "전입신고는 언제까지 해야 하나요?" });
  await option.click();
  await expect(page.getByText(successResponse.summary)).toBeVisible();

  expect(requests).toHaveLength(2);
  expect(requests[1].question).toBe("전입신고는 언제까지 해야 하나요?");
  expect(requests[1].context_token).toBe("signed-followup-context");
  // 선택 직후 카드는 요약형으로 전환 - 선택지 버튼은 사라진다
  await expect(option).toHaveCount(0);
  expect(await page.context().cookies()).toEqual([]);
  expect(
    await page.evaluate(async () => ({
      indexedDbCount: (await indexedDB.databases()).length,
      localStorageCount: localStorage.length,
      sessionStorageCount: sessionStorage.length,
    })),
  ).toEqual({ indexedDbCount: 0, localStorageCount: 0, sessionStorageCount: 0 });
});

test("privacy and unavailable states stay value-free, accessible, and within the viewport", async ({ page }) => {
  let calls = 0;
  await page.route("**/api/v1/chat", async (route) => {
    calls += 1;
    if (calls === 1) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          request_id: "33333333-3333-4333-8333-333333333333",
          answer_status: "FALLBACK",
          intent: "UNKNOWN",
          confidence: null,
          summary: null,
          procedure_steps: [],
          required_documents: [],
          processing_time: null,
          fee: null,
          department: null,
          sources: [],
          office: null,
          followup_options: [],
          fallback: {
            reason: "PRIVACY_UNRESOLVED",
            title: "개인정보를 안전하게 처리하지 못했어요",
            message: "개인정보를 빼거나 표현을 바꿔서 다시 질문해 주세요.",
            next_actions: ["이름, 주소, 전화번호, 접수번호 등을 적지 마세요."],
            candidate_eligible: false,
            office: null,
          },
          context_token: null,
        }),
      });
      return;
    }
    await route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({
        error: {
          code: "SERVICE_UNAVAILABLE",
          message: "잠시 후 다시 시도해 주세요.",
          request_id: "44444444-4444-4444-8444-444444444444",
          retryable: true,
        },
      }),
    });
  });

  await page.goto("/chat");
  await submit(page, "개인정보가 포함된 질문");
  await expect(page.getByText("개인정보를 안전하게 처리하지 못했어요")).toBeVisible();
  await expect(page.getByText("이름, 주소, 전화번호, 접수번호 등을 적지 마세요.")).toBeVisible();
  await submit(page, "일시 오류 확인");
  await expect(
    page.getByRole("alert").filter({ hasText: "연결 오류" }),
  ).toContainText("지금은 안전한 답변을 만들 수 없어요.");
  await expect(page.getByRole("button", { name: "다시 시도" })).toBeVisible();

  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
    ),
  ).toBe(true);
  const question = page.getByRole("textbox", { name: "질문 입력" });
  await question.focus();
  await expect(question).toBeFocused();
  const focusStyle = await question.evaluate((element) => {
    const style = getComputedStyle(element);
    return { outlineStyle: style.outlineStyle, boxShadow: style.boxShadow };
  });
  expect(focusStyle.outlineStyle !== "none" || focusStyle.boxShadow !== "none").toBe(true);

  // 개인정보 경고 문구의 명도 대비 4.5:1 이상 (QUR-001)
  const ratio = await page
    .locator("p", { hasText: "개인정보는 입력하지 마세요" })
    .last()
    .evaluate((element) => {
      const parse = (value: string) =>
        value.match(/\d+/g)!.slice(0, 3).map(Number) as [number, number, number];
      const color = parse(getComputedStyle(element).color);
      const background = parse(getComputedStyle(document.body).backgroundColor);
      const luminance = (rgb: [number, number, number]) => {
        const linear = rgb.map((channel) => {
          const value = channel / 255;
          return value <= 0.03928 ? value / 12.92 : Math.pow((value + 0.055) / 1.055, 2.4);
        });
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2];
      };
      const [lighter, darker] = [luminance(color), luminance(background)].sort((a, b) => b - a);
      return (lighter + 0.05) / (darker + 0.05);
    });
  expect(ratio).toBeGreaterThanOrEqual(4.5);
});

test("retry keeps one idempotency identity and a new question rotates it without browser persistence", async ({ page }) => {
  const requestHeaders: Record<string, string>[] = [];
  let calls = 0;
  await page.route("**/api/v1/chat", async (route) => {
    calls += 1;
    requestHeaders.push(route.request().headers());
    if (calls === 1) {
      await route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({
          error: {
            code: "SERVICE_UNAVAILABLE",
            message: "잠시 후 다시 시도해 주세요.",
            request_id: "44444444-4444-4444-8444-444444444444",
            retryable: true,
          },
        }),
      });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        ...successResponse,
        request_id: calls === 2
          ? "55555555-5555-4555-8555-555555555555"
          : "66666666-6666-4666-8666-666666666666",
      }),
    });
  });

  await page.goto("/chat");
  await submit(page, "재시도할 질문");
  await page.getByRole("button", { name: "다시 시도" }).click();
  await expect(page.getByText(successResponse.summary)).toBeVisible();
  await submit(page, "새 질문");
  await expect(page.getByText(successResponse.summary)).toHaveCount(2);

  const keys = requestHeaders.map((headers) => headers["idempotency-key"]);
  expect(keys[0]).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i);
  expect(keys[1]).toBe(keys[0]);
  expect(keys[2]).not.toBe(keys[0]);
  expect(requestHeaders.every((headers) => headers["x-request-id"] === undefined)).toBe(true);
  expect(page.url()).toBe("http://127.0.0.1:3001/chat");
  expect(await page.context().cookies()).toEqual([]);
  expect(
    await page.evaluate(async () => ({
      indexedDbCount: (await indexedDB.databases()).length,
      localStorageCount: localStorage.length,
      sessionStorageCount: sessionStorage.length,
    })),
  ).toEqual({ indexedDbCount: 0, localStorageCount: 0, sessionStorageCount: 0 });
});
