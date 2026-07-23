import { expect, test, type Page } from "@playwright/test";

type JsonObject = Readonly<Record<string, unknown>>;

const PERSONAL_LOOKUP_QUESTION = "내 자동차세 체납액 알려줘.";
const INSUFFICIENT_GROUNDING_QUESTION = "침대 2인용 프레임 수수료가 얼마예요?";
const CANDIDATE_TITLE = "침대 프레임 배출 수수료";
const OFFICIAL_SOURCE_TITLE = "배출항목선택";
const OFFICIAL_SOURCE_URL =
  "https://www.sjwaste.kr/wasteApp/appCategoryPopup.do?menuId=MENU00305";

async function submit(page: Page, question: string) {
  const textbox = page.getByRole("textbox", { name: "민원 질문" });
  await textbox.fill(question);
  await page.getByRole("button", { name: "질문 보내기" }).click();
}

function requireObject(value: unknown, label: string): JsonObject {
  if (typeof value !== "object" || value == null || Array.isArray(value)) {
    throw new Error(`Expected a JSON object for ${label}.`);
  }
  return value as JsonObject;
}

async function submitAndReadChatResponse(page: Page, question: string): Promise<JsonObject> {
  const responsePromise = page.waitForResponse((response) => {
    const url = new URL(response.url());
    return url.pathname === "/api/v1/chat" && response.request().method() === "POST";
  });

  await submit(page, question);
  const response = await responsePromise;
  expect(response.status()).toBe(200);
  return requireObject(await response.json(), "chat response");
}

async function openActualAdminDashboard(page: Page) {
  const failedQuestionsResponse = page.waitForResponse((response) => {
    const url = new URL(response.url());
    return url.pathname === "/api/v1/admin/failed-questions"
      && response.request().method() === "GET";
  });
  const candidatesResponse = page.waitForResponse((response) => {
    const url = new URL(response.url());
    return url.pathname === "/api/v1/admin/kb-candidates"
      && response.request().method() === "GET";
  });

  await page.goto("/admin");
  const [failedQuestions, candidates] = await Promise.all([
    failedQuestionsResponse,
    candidatesResponse,
  ]);
  expect(failedQuestions.status()).toBe(200);
  expect(candidates.status()).toBe(200);
  await expect(
    page.getByText("실제 local DB API 연결"),
    "Run the web server with ADMIN_UI_MODE=actual for this opt-in test.",
  ).toBeVisible();
  await expect(
    page.getByRole("region", { name: "실패 질문", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("region", { name: "KB 후보와 ACTIVE 상태", exact: true }),
  ).toBeVisible();
  await expect(page.getByRole("main").getByRole("alert")).toHaveCount(0);
}

function requireFallback(response: JsonObject): JsonObject {
  if (response.answer_status !== "FALLBACK") {
    throw new Error("Expected a contract-valid FALLBACK response.");
  }
  return requireObject(response.fallback, "fallback");
}

function requireSources(response: JsonObject): readonly unknown[] {
  if (!Array.isArray(response.sources)) {
    throw new Error("Expected a source array in the SUCCESS response.");
  }
  return response.sources;
}

const actualLocalE2eEnabled =
  (globalThis as { process?: { env?: Record<string, string | undefined> } })
    .process?.env?.SEJONG_ACTUAL_LOCAL_E2E === "true";

test.describe("opt-in actual local/private citizen-to-admin improvement loop", () => {
  test.skip(
    !actualLocalE2eEnabled,
    "Set SEJONG_ACTUAL_LOCAL_E2E=true only after the clean local DB is reset and seeded to 19 ACTIVE.",
  );

  test("keeps personal lookup separate and promotes a distinct grounded failure to the 20th ACTIVE KB", async (
    { page },
    testInfo,
  ) => {
    test.setTimeout(120_000);
    test.skip(
      testInfo.project.name !== "desktop",
      "The state-changing 19-to-20 actual loop must run exactly once, not once per viewport project.",
    );

    await openActualAdminDashboard(page);

    await page.goto("/chat");

    const personalLookup = await submitAndReadChatResponse(page, PERSONAL_LOOKUP_QUESTION);
    expect(personalLookup.answer_status).toBe("FALLBACK");
    expect(personalLookup.intent).toBe("UNKNOWN");
    const personalFallback = requireFallback(personalLookup);
    expect(personalFallback.reason).toBe("PERSONAL_LOOKUP");
    expect(personalFallback.candidate_eligible).toBe(false);
    await expect(page.locator(".answer-fallback").last()).toContainText("PERSONAL_LOOKUP");

    const insufficientGrounding = await submitAndReadChatResponse(
      page,
      INSUFFICIENT_GROUNDING_QUESTION,
    );
    expect(insufficientGrounding.answer_status).toBe("FALLBACK");
    expect(insufficientGrounding.intent).toBe("BULKY_WASTE");
    const groundingFallback = requireFallback(insufficientGrounding);
    expect(groundingFallback.reason).toBe("INSUFFICIENT_GROUNDING");
    expect(groundingFallback.candidate_eligible).toBe(true);
    await expect(page.locator(".answer-fallback").last()).toContainText(
      "INSUFFICIENT_GROUNDING",
    );

    await openActualAdminDashboard(page);
    await page
      .getByRole("button", { name: INSUFFICIENT_GROUNDING_QUESTION })
      .click();
    const failureDetail = page.getByRole("region", {
      name: "실패 질문 상세",
      exact: true,
    });
    await failureDetail.getByRole("button", { name: "사유 확정" }).click();
    await expect(
      failureDetail.getByText("사유 확인 완료", { exact: true }),
    ).toBeVisible();

    await page
      .getByRole("button", { name: "검수된 KB-WASTE-03 자료 불러오기" })
      .click();
    await expect(page.getByRole("textbox", { name: "후보 제목" })).toHaveValue(
      CANDIDATE_TITLE,
    );
    await page.getByRole("button", { name: "KB 후보 작성" }).click();

    let candidate = page.getByRole("article", { name: CANDIDATE_TITLE });
    await expect(candidate).toBeVisible();
    await candidate.getByRole("button", { name: "승인 요청" }).click();
    await expect(candidate).toContainText("승인 대기");

    await page.getByRole("combobox", { name: "시연 역할" }).selectOption("APPROVER");
    candidate = page.getByRole("article", { name: CANDIDATE_TITLE });
    await expect(candidate).toContainText("작성 OPERATOR-LOCAL-001");
    await candidate.getByRole("textbox", { name: "검수 의견" }).fill("공식 품목표 정본 확인");
    await candidate.getByRole("button", { name: "승인하고 ACTIVE 반영" }).click();
    await expect(candidate).toContainText("ACTIVE 반영 완료");
    await expect(candidate).toContainText("검수 PM-LOCAL-001");

    await page.goto("/chat");
    const improved = await submitAndReadChatResponse(
      page,
      INSUFFICIENT_GROUNDING_QUESTION,
    );
    expect(improved.answer_status).toBe("SUCCESS");
    expect(improved.intent).toBe("BULKY_WASTE");
    expect(requireSources(improved)).toContainEqual(
      expect.objectContaining({
        source_id: "KB-WASTE-03",
        title: OFFICIAL_SOURCE_TITLE,
        url: OFFICIAL_SOURCE_URL,
      }),
    );

    await expect(page.locator(".answer-success").last()).toContainText(
      "공식 근거를 확인했어요",
    );
    await expect(
      page.getByRole("link", { name: OFFICIAL_SOURCE_TITLE }).last(),
    ).toHaveAttribute("href", OFFICIAL_SOURCE_URL);
  });
});
