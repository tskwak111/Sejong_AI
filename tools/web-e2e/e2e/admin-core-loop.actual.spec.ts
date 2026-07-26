import { expect, test, type Page } from "@playwright/test";

type JsonObject = Readonly<Record<string, unknown>>;

type FailedQuestion = Readonly<{
  id: string;
  masked_question: string | null;
  fallback_reason: string;
  candidate_eligible: boolean;
  status: string;
}>;

const OPERATOR_HEADERS = {
  "X-Demo-Actor-Id": "OPERATOR-LOCAL-001",
  "X-Demo-Role": "OPERATOR",
} as const;

const PERSONAL_LOOKUP_QUESTION = "내 자동차세 체납액 알려줘.";
const INSUFFICIENT_GROUNDING_QUESTION = "침대 2인용 프레임 수수료가 얼마예요?";
const CANDIDATE_TITLE = "침대 프레임 배출 수수료";

async function fillOfficialCandidate(page: Page) {
  await page.getByLabel("제목").fill(CANDIDATE_TITLE);
  await page.getByLabel("답변 요약").fill(
    "공식 품목표의 침대 프레임 수수료는 1인용침대 8,000원, 2인용침대 10,000원으로 표시됩니다.",
  );
  await page.getByLabel("처리 절차 (한 줄에 한 단계)").fill(
    "공식 품목표에서 침대 프레임의 1인용침대 또는 2인용침대 항목을 확인합니다.\n해당 수수료로 공식 배출 절차를 진행합니다.",
  );
  await page.getByLabel("수수료 (선택)").fill(
    "1인용침대 8,000원; 2인용침대 10,000원",
  );
  await page.getByLabel("담당 부서").fill("세종특별자치시시설관리공단");
  await page.getByLabel("공식 출처명").fill("배출항목선택");
  await page.getByLabel("공식 출처 URL").fill(
    "https://www.sjwaste.kr/wasteApp/appCategoryPopup.do?menuId=MENU00305",
  );
  await page.getByLabel("출처 확인일").fill("2026-07-18");
  await page.getByLabel("주의사항 (선택)").fill(
    "공식 품목표의 1인용침대·2인용침대 항목을 그대로 따릅니다. 매트리스 포함 가격이나 실제 규격을 단정하지 않습니다.",
  );
  await page.getByRole("button", { name: "후보 저장 후 승인 요청" }).click();
}
const OFFICIAL_SOURCE_TITLE = "배출항목선택";
const OFFICIAL_SOURCE_URL =
  "https://www.sjwaste.kr/wasteApp/appCategoryPopup.do?menuId=MENU00305";

function requireObject(value: unknown, label: string): JsonObject {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new Error(`Expected a JSON object for ${label}.`);
  }
  return value as JsonObject;
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

async function submitAndReadChatResponse(
  page: Page,
  question: string,
): Promise<JsonObject> {
  const responsePromise = page.waitForResponse((response) => {
    const url = new URL(response.url());
    return (
      url.pathname === "/api/v1/chat" &&
      response.request().method() === "POST"
    );
  });

  await page.getByRole("textbox", { name: "질문 입력" }).fill(question);
  await page.getByRole("button", { name: "전송" }).click();

  const response = await responsePromise;
  expect(response.status()).toBe(200);
  return requireObject(await response.json(), "chat response");
}

async function listFailedQuestions(page: Page): Promise<readonly FailedQuestion[]> {
  const response = await page.request.get("/api/v1/admin/failed-questions", {
    headers: OPERATOR_HEADERS,
  });
  expect(response.status()).toBe(200);
  const payload = requireObject(await response.json(), "failed-question list");
  if (!Array.isArray(payload.items)) {
    throw new Error("Expected failed-question items.");
  }
  return payload.items.map((item) => {
    const candidate = requireObject(item, "failed-question item");
    if (
      typeof candidate.id !== "string" ||
      (typeof candidate.masked_question !== "string" &&
        candidate.masked_question !== null) ||
      typeof candidate.fallback_reason !== "string" ||
      typeof candidate.candidate_eligible !== "boolean" ||
      typeof candidate.status !== "string"
    ) {
      throw new Error("Expected a contract-valid failed-question item.");
    }
    return {
      id: candidate.id,
      masked_question: candidate.masked_question,
      fallback_reason: candidate.fallback_reason,
      candidate_eligible: candidate.candidate_eligible,
      status: candidate.status,
    };
  });
}

function sortedIds(items: readonly FailedQuestion[]): readonly string[] {
  return items.map((item) => item.id).sort();
}

/**
 * State-changing local/private evidence. Run once only after the disposable DB
 * is reset and seeded to the approved 19 ACTIVE baseline. The backend runner
 * owns the exact 19→20 count proof; this browser test proves the real
 * frontend→API→DB workflow and the final server-owned public source identity.
 */
test("actual browser keeps PERSONAL unpersisted and promotes a separate IG question to KB-WASTE-03", async ({
  page,
}) => {
  test.setTimeout(120_000);

  const ready = await page.request.get("http://127.0.0.1:8000/ready");
  expect(ready.status()).toBe(200);

  const initialFailures = await listFailedQuestions(page);

  await page.goto("/chat");
  const personalLookup = await submitAndReadChatResponse(
    page,
    PERSONAL_LOOKUP_QUESTION,
  );
  expect(personalLookup.answer_status).toBe("FALLBACK");
  expect(personalLookup.intent).toBe("UNKNOWN");
  expect(requireFallback(personalLookup)).toMatchObject({
    reason: "PERSONAL_LOOKUP",
    candidate_eligible: false,
  });
  await expect(
    page.getByText("질문 내용은 저장되지 않았습니다.", { exact: true }).last(),
  ).toBeVisible();

  const afterPersonal = await listFailedQuestions(page);
  expect(sortedIds(afterPersonal)).toEqual(sortedIds(initialFailures));

  const insufficientGrounding = await submitAndReadChatResponse(
    page,
    INSUFFICIENT_GROUNDING_QUESTION,
  );
  expect(insufficientGrounding.answer_status).toBe("FALLBACK");
  expect(insufficientGrounding.intent).toBe("BULKY_WASTE");
  expect(requireFallback(insufficientGrounding)).toMatchObject({
    reason: "INSUFFICIENT_GROUNDING",
    candidate_eligible: true,
  });
  await expect(
    page
      .getByText(
        "이 질문은 안내 개선을 위해 개인정보를 가린 채 30일간만 보관돼요.",
        { exact: true },
      )
      .last(),
  ).toBeVisible();

  const afterGrounding = await listFailedQuestions(page);
  expect(afterGrounding).toHaveLength(afterPersonal.length + 1);
  const priorFailureIds = new Set(afterPersonal.map((item) => item.id));
  const newFailures = afterGrounding.filter(
    (item) => !priorFailureIds.has(item.id),
  );
  expect(newFailures).toHaveLength(1);
  expect(newFailures[0]).toMatchObject({
    masked_question: INSUFFICIENT_GROUNDING_QUESTION,
    fallback_reason: "INSUFFICIENT_GROUNDING",
    candidate_eligible: true,
    status: "NEW",
  });

  await page.goto("/admin/failures");
  await expect(
    page.getByRole("heading", { name: "답변 실패 질문 관리" }),
  ).toBeVisible();

  const targetRow = () =>
    page
      .locator("tr")
      .filter({ hasText: INSUFFICIENT_GROUNDING_QUESTION })
      .first();
  await expect(targetRow()).toBeVisible();
  await targetRow().getByRole("button", { name: "사유 확정" }).click();
  await expect(
    page.getByText("사유가 확정되었습니다").filter({ visible: true }).first(),
  ).toBeVisible();

  await targetRow().getByRole("button", { name: "KB 후보 생성" }).click();
  await fillOfficialCandidate(page);
  await expect(
    page
      .getByText(/운영자가 작성한 KB 후보가 승인 요청되었습니다/)
      .filter({ visible: true })
      .first(),
  ).toBeVisible();
  await page.getByRole("link", { name: "KB 후보 승인으로 이동" }).click();

  await expect(page.getByRole("heading", { name: "KB 후보 승인" })).toBeVisible();
  await expect(
    page.getByRole("heading", { name: CANDIDATE_TITLE }),
  ).toBeVisible();
  await expect(page.getByText("작성 OPERATOR-LOCAL-001").first()).toBeVisible();

  await page.locator("#demo-role").selectOption("APPROVER");
  const checkboxes = page.getByRole("checkbox");
  await expect(checkboxes).toHaveCount(3);
  for (const checkbox of await checkboxes.all()) {
    await checkbox.check();
  }

  await page
    .getByRole("textbox", { name: "검수 의견 (필수)" })
    .fill("공식 품목표 원문과 정본 필드를 대조했습니다.");
  const approve = page.getByRole("button", {
    name: "승인하고 ACTIVE 반영",
  });
  await expect(approve).toBeEnabled();
  await approve.click();

  await expect(
    page.getByText("KB 문서가 ACTIVE로 반영되었습니다").filter({ visible: true }),
  ).toBeVisible();
  await expect(page.getByText("다음 시민 답변부터 사용됩니다.")).toBeVisible();

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
  await expect(page.getByText(OFFICIAL_SOURCE_TITLE, { exact: true }).last()).toBeVisible();
  await expect(
    page.getByRole("link", { name: "원문 보기" }).last(),
  ).toHaveAttribute("href", OFFICIAL_SOURCE_URL);
});
