import { expect, test } from "@playwright/test";

test("127.0.0.1 dev origin may load Next resources from the hydrated dev server", async ({
  page,
}) => {
  const failedNextRequests: string[] = [];
  const badNextStatuses: number[] = [];

  page.on("requestfailed", (request) => {
    if (request.url().includes("/_next/")) {
      failedNextRequests.push(request.url());
    }
  });
  page.on("response", (response) => {
    if (response.url().includes("/_next/") && response.status() >= 400) {
      badNextStatuses.push(response.status());
    }
  });

  const response = await page.goto("/", { waitUntil: "networkidle" });
  expect(response?.status()).toBe(200);

  const questionInput = page.getByLabel("질문 입력");
  await expect(questionInput).toHaveAttribute(
    "placeholder",
    "예: 전입신고는 언제까지 해야 하나요?",
  );
  await questionInput.focus();
  await expect(questionInput).toHaveAttribute(
    "placeholder",
    "예: 아름동에서 대형폐기물은 언제 내놓나요?",
    { timeout: 5_000 },
  );

  const nextAsset = await page.evaluate(() =>
    performance
      .getEntriesByType("resource")
      .map((entry) => entry.name)
      .find((name) => name.includes("/_next/")),
  );
  expect(nextAsset).toBeTruthy();
  const crossOriginResponse = await page.request.get(nextAsset!, {
    headers: {
      referer: "http://127.0.0.1:3001/",
      "sec-fetch-mode": "no-cors",
      "sec-fetch-site": "cross-site",
    },
  });
  expect(crossOriginResponse.status()).toBe(200);

  expect(failedNextRequests).toEqual([]);
  expect(badNextStatuses).toEqual([]);
});
