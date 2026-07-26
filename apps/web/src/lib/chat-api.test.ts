import { describe, expect, it, vi } from "vitest";

import type { ChatResponse } from "./chat-api";
import { ChatTransportError, createChatTransport } from "./chat-api";

const SUCCESS_RESPONSE = {
  request_id: "11111111-1111-4111-8111-111111111111",
  answer_status: "SUCCESS",
  answer_mode: "TEMPLATE",
  intent: "MOVE_IN_RESIDENT_REGISTRATION",
  sources: [
    {
      source_id: "source-001",
      title: "세종시 전입신고 안내",
      url: "https://example.invalid/move-in",
      last_verified_at: "2026-07-20",
    },
  ],
  office: null,
  context_token: "signed-token",
} satisfies ChatResponse;

describe("chat API transport", () => {
  it("posts the generated request shape to the configured v1 chat endpoint", async () => {
    const fetcher = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(SUCCESS_RESPONSE), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    const transport = createChatTransport("http://127.0.0.1:8000/", fetcher);

    await expect(
      transport.send({
        question: "전입신고 알려줘",
        selected_region: "아름동",
        simple_language: false,
        context_token: null,
      }),
    ).resolves.toEqual(SUCCESS_RESPONSE);
    expect(fetcher).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/api/v1/chat",
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: "전입신고 알려줘",
          selected_region: "아름동",
          simple_language: false,
          context_token: null,
        }),
      }),
    );
  });

  it("adds an optional idempotency identity without inventing a correlation request id", async () => {
    const fetcher = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(SUCCESS_RESPONSE), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    const transport = createChatTransport(undefined, fetcher);

    await transport.send(
      { question: "전입신고 알려줘" },
      { idempotencyKey: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa" },
    );

    expect(fetcher).toHaveBeenCalledWith(
      "/api/v1/chat",
      expect.objectContaining({
        headers: {
          "Content-Type": "application/json",
          "Idempotency-Key": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        },
      }),
    );
    const init = fetcher.mock.calls[0][1] as RequestInit;
    expect(init.headers).not.toHaveProperty("X-Request-Id");
  });

  it("uses same-origin by default and maps non-200 responses to a value-free retryable error", async () => {
    const fetcher = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          error: {
            code: "SERVICE_UNAVAILABLE",
            message: "upstream implementation detail",
            request_id: "55555555-5555-4555-8555-555555555555",
            retryable: true,
          },
        }),
        { status: 503, headers: { "content-type": "application/json" } },
      ),
    );
    const transport = createChatTransport(undefined, fetcher);

    const error = await transport.send({ question: "민원 안내" }).catch((value: unknown) => value);

    expect(fetcher).toHaveBeenCalledWith("/api/v1/chat", expect.any(Object));
    expect(error).toBeInstanceOf(ChatTransportError);
    expect(error).toMatchObject({ status: 503, retryable: true });
    expect((error as Error).message).not.toContain("upstream implementation detail");
  });
});
