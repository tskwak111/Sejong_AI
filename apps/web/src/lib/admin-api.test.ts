import { describe, expect, it, vi } from "vitest";

import {
  AdminTransportError,
  type AdminActor,
  createAdminTransport,
} from "./admin-api";

const ACTOR = {
  actorId: "OPERATOR-LOCAL-001",
  role: "OPERATOR",
} satisfies AdminActor;

const ID = "11111111-1111-4111-8111-111111111111";
const CANDIDATE_ID = "22222222-2222-4222-8222-222222222222";

function json(value: unknown, status = 200) {
  return new Response(JSON.stringify(value), {
    status,
    headers: { "content-type": "application/json" },
  });
}

describe("actual local/private admin API transport", () => {
  it("maps all nine contract operations to same-origin requests with fixed actor headers", async () => {
    const fetcher = vi.fn()
      .mockResolvedValueOnce(json({ items: [], total: 0 }))
      .mockResolvedValueOnce(json({ item: { id: ID } }))
      .mockResolvedValueOnce(json({ id: ID, status: "REASON_CONFIRMED" }))
      .mockResolvedValueOnce(json({ items: [], total: 0 }))
      .mockResolvedValueOnce(json({ id: ID, status: "PLANNED" }))
      .mockResolvedValueOnce(json({ items: [], total: 0 }))
      .mockResolvedValueOnce(json({ id: CANDIDATE_ID, status: "DRAFTED" }, 201))
      .mockResolvedValueOnce(json({ id: CANDIDATE_ID, status: "PENDING_APPROVAL" }))
      .mockResolvedValueOnce(json({ id: CANDIDATE_ID, status: "REJECTED" }));
    const transport = createAdminTransport(fetcher);
    const candidate = {
      failed_question_id: ID,
      category: "BULKY_WASTE" as const,
      title: "침대 프레임 배출 안내",
      representative_question: "침대 프레임은 어떻게 버리나요?",
      answer_summary: "신고 후 배출해요.",
      procedure_steps: [],
      required_documents: [],
      processing_time: null,
      fee: null,
      department: "자원순환 담당",
      caution: null,
      source_title: "세종특별자치시 공식 안내",
      source_url: "https://example.invalid/official/waste",
      last_verified_at: "2026-07-20",
    };

    await transport.listFailedQuestions(ACTOR);
    await transport.getFailedQuestion(ACTOR, ID);
    await transport.confirmReason(ACTOR, ID, { reason: "INSUFFICIENT_GROUNDING" });
    await transport.listCivicScopeGaps(ACTOR, "NEW");
    await transport.reviewCivicScopeGap(
      { actorId: "PM-LOCAL-001", role: "APPROVER" },
      ID,
      { decision: "PLANNED", review_comment: "다음 범위로 검토" },
    );
    await transport.listCandidates(ACTOR);
    await transport.createCandidate(ACTOR, candidate);
    await transport.submitCandidate(ACTOR, CANDIDATE_ID);
    await transport.reviewCandidate(
      { actorId: "PM-LOCAL-001", role: "APPROVER" },
      CANDIDATE_ID,
      { decision: "REJECTED", review_comment: "근거 보완 필요" },
    );

    expect(fetcher.mock.calls.map(([url, init]) => [url, init?.method])).toEqual([
      ["/api/v1/admin/failed-questions", "GET"],
      [`/api/v1/admin/failed-questions/${ID}`, "GET"],
      [`/api/v1/admin/failed-questions/${ID}/reason`, "PATCH"],
      ["/api/v1/admin/civic-scope-gaps?status=NEW", "GET"],
      [`/api/v1/admin/civic-scope-gaps/${ID}/review`, "PATCH"],
      ["/api/v1/admin/kb-candidates", "GET"],
      ["/api/v1/admin/kb-candidates", "POST"],
      [`/api/v1/admin/kb-candidates/${CANDIDATE_ID}/submit`, "POST"],
      [`/api/v1/admin/kb-candidates/${CANDIDATE_ID}/review`, "PATCH"],
    ]);

    for (const [, init] of fetcher.mock.calls.slice(0, 4)) {
      expect(init?.headers).toMatchObject({
        "X-Demo-Actor-Id": "OPERATOR-LOCAL-001",
        "X-Demo-Role": "OPERATOR",
      });
      expect(init?.headers).not.toHaveProperty("X-Request-Id");
    }
    expect(fetcher.mock.calls[4][1]?.headers).toMatchObject({
      "X-Demo-Actor-Id": "PM-LOCAL-001",
      "X-Demo-Role": "APPROVER",
    });
    for (const [, init] of fetcher.mock.calls.slice(5, 8)) {
      expect(init?.headers).toMatchObject({
        "X-Demo-Actor-Id": "OPERATOR-LOCAL-001",
        "X-Demo-Role": "OPERATOR",
      });
    }
    expect(fetcher.mock.calls[8][1]?.headers).toMatchObject({
      "X-Demo-Actor-Id": "PM-LOCAL-001",
      "X-Demo-Role": "APPROVER",
    });
    expect(fetcher.mock.calls[2][1]?.body).toBe(JSON.stringify({
      reason: "INSUFFICIENT_GROUNDING",
    }));
    expect(fetcher.mock.calls[4][1]?.body).toBe(JSON.stringify({
      decision: "PLANNED",
      review_comment: "다음 범위로 검토",
    }));
    expect(fetcher.mock.calls[6][1]?.body).toBe(JSON.stringify(candidate));
    expect(fetcher.mock.calls[8][1]?.body).toBe(JSON.stringify({
      decision: "REJECTED",
      review_comment: "근거 보완 필요",
    }));
  });

  it("maps backend failures to a value-free error without echoing response content", async () => {
    const fetcher = vi.fn().mockResolvedValue(
      json({ error: { message: "raw question and database detail" } }, 503),
    );
    const transport = createAdminTransport(fetcher);

    const error = await transport.listFailedQuestions(ACTOR).catch((value: unknown) => value);

    expect(error).toBeInstanceOf(AdminTransportError);
    expect(error).toMatchObject({ status: 503, retryable: true });
    expect((error as Error).message).not.toContain("raw question");
    expect((error as Error).message).not.toContain("database");
  });
});
