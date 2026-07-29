import { describe, expect, it, vi } from "vitest";

import {
  FeedbackTransportError,
  createFeedbackTransport,
  createFixtureFeedbackTransport,
} from "./feedback-api";

const REQUEST = {
  request_id: "11111111-1111-4111-8111-111111111111",
  rating: "DISSATISFIED",
  category: "OTHER",
  reason_code: "OTHER",
  detail: "설명이 더 구체적이면 좋겠어요.",
} as const;

describe("citizen feedback transport", () => {
  it("posts only the approved feedback fields to the same-origin endpoint", async () => {
    const fetcher = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          request_id: REQUEST.request_id,
          status: "RECORDED",
          detail_status: "STORED",
        }),
        { status: 201, headers: { "content-type": "application/json" } },
      ),
    );

    const result = await createFeedbackTransport(fetcher).record(REQUEST);

    expect(result.status).toBe("RECORDED");
    expect(fetcher).toHaveBeenCalledWith("/api/v1/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(REQUEST),
    });
  });

  it("returns a value-free error without exposing the server body", async () => {
    const fetcher = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "sensitive internal detail" }), {
        status: 503,
      }),
    );

    const error = await createFeedbackTransport(fetcher)
      .record(REQUEST)
      .catch((value: unknown) => value);

    expect(error).toBeInstanceOf(FeedbackTransportError);
    expect(error).toMatchObject({ status: 503, retryable: true });
    expect((error as Error).message).not.toContain("sensitive");
  });

  it("keeps fixture feedback in memory without a network call", async () => {
    const fixture = createFixtureFeedbackTransport();

    await expect(fixture.record(REQUEST)).resolves.toMatchObject({
      request_id: REQUEST.request_id,
      status: "RECORDED",
    });
  });
});
