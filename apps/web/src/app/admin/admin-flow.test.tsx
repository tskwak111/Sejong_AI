// @vitest-environment jsdom

/**
 * 이음센터 핵심 루프 테스트 - 계약 fixture 흐름 검증 (데모 #5):
 * 실패 질문 큐(NEW) → 사유 확정(REASON_CONFIRMED) → 근거 부족 건만 KB 후보
 * 생성(DRAFTED→PENDING_APPROVAL) → 별도 승인자 검수(review_comment 필수) →
 * 공식 출처(OFFICIAL) 후보만 ACTIVE 승인. MOCK 승인 금지·자기검수 금지 유지.
 */
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  buildCandidateDraft,
  CURATED_ISG_FAILURE_ID,
  getFixtureAdminTransport,
  resetDemoStore,
  routeDemoAnswer,
} from "../../lib/demo-fixtures";
import type { AdminActor } from "../../lib/admin-api";
import AdminShell from "../../components/admin/AdminShell";
import AdminFailuresPage from "./failures/page";
import AdminKbCandidatesPage from "./kb-candidates/page";

let mockPathname = "/admin/failures";

vi.mock("next/navigation", async () => {
  const actual = await vi.importActual<typeof import("next/navigation")>(
    "next/navigation",
  );
  return {
    ...actual,
    usePathname: () => mockPathname,
    useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  };
});

const OPERATOR: AdminActor = { role: "OPERATOR", actorId: "OPERATOR-LOCAL-001" };
const APPROVER: AdminActor = { role: "APPROVER", actorId: "PM-LOCAL-001" };

async function curatedFailure() {
  const transport = getFixtureAdminTransport();
  const list = await transport.listFailedQuestions(OPERATOR);
  const failure = list.items.find((f) => f.id === CURATED_ISG_FAILURE_ID);
  if (!failure) throw new Error("curated fixture missing");
  return failure;
}

beforeEach(() => {
  resetDemoStore();
  mockPathname = "/admin/failures";
});

describe("failures screen (fixture)", () => {
  it("renders masked, purged and personal-lookup rows without breaking", async () => {
    render(
      <AdminShell mode="fixture">
        <AdminFailuresPage />
      </AdminShell>,
    );

    expect(
      (
        await screen.findAllByText(
          "전입신고를 대리인이 하면 위임장 공증이 필요한가요?",
        )
      ).length,
    ).toBeGreaterThan(0);
    expect(screen.getAllByText("제 자동차세 얼마 나왔나요?").length).toBeGreaterThan(0);
    // 30일 파기 행 - NULL이어도 깨지지 않는다 (테이블 + 모바일 카드 각 1회)
    expect(
      screen.getAllByText(/보관 기간 경과/).length,
    ).toBeGreaterThan(0);
    // 저장 사유 필터는 3종 + 전체 (OUT_OF_SCOPE 필터 없음)
    expect(screen.getByRole("button", { name: /^전체 / })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^근거 부족 / })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^개인별 조회 / })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^법적 판단 / })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /범위 밖/ })).not.toBeInTheDocument();
  });

  it("lets the operator confirm a reason and create a KB candidate for grounding failures only", async () => {
    render(
      <AdminShell mode="fixture">
        <AdminFailuresPage />
      </AdminShell>,
    );
    await screen.findAllByText(
      "전입신고를 대리인이 하면 위임장 공증이 필요한가요?",
    );

    // NEW 행 2건(ISG + PERSONAL) - 사유 확정 버튼 노출 (테이블/모바일 중복 렌더)
    const confirmButtons = screen.getAllByRole("button", { name: "사유 확정" });
    expect(confirmButtons.length).toBeGreaterThan(0);

    // 근거 부족 건 사유 확정 → KB 후보 생성 버튼 등장
    const isgRow = screen
      .getAllByText("전입신고를 대리인이 하면 위임장 공증이 필요한가요?")[0]
      .closest("tr, article") as HTMLElement;
    fireEvent.click(
      (isgRow.querySelector("button") as HTMLButtonElement),
    );

    await waitFor(() =>
      expect(screen.getAllByText("사유가 확정되었습니다").length).toBeGreaterThan(0),
    );
    const createButtons = await screen.findAllByRole("button", {
      name: "KB 후보 생성",
    });
    fireEvent.click(createButtons[0]);

    await waitFor(() =>
      expect(
        screen.getAllByText(/KB 후보 초안이 생성되었습니다/).length,
      ).toBeGreaterThan(0),
    );
    // 승인 화면 이동 배너 (데모 #5 전환)
    expect(
      screen.getByRole("link", { name: "KB 후보 승인으로 이동" }),
    ).toHaveAttribute("href", "/admin/kb-candidates");
    // 중복 생성 방지
    expect(
      screen.getAllByRole("button", { name: "초안 생성됨" }).length,
    ).toBeGreaterThan(0);
  });
});

describe("kb candidate approval screen (fixture)", () => {
  async function seedPendingCuratedCandidate() {
    const transport = getFixtureAdminTransport();
    const failure = await curatedFailure();
    await transport.confirmReason(OPERATOR, failure.id, {
      reason: failure.fallback_reason,
    });
    const draft = buildCandidateDraft(failure);
    const created = await transport.createCandidate(OPERATOR, draft);
    await transport.submitCandidate(OPERATOR, created.id);
    return created.id;
  }

  it("requires the approver role and a review comment, then approves an OFFICIAL draft to ACTIVE", async () => {
    await seedPendingCuratedCandidate();
    mockPathname = "/admin/kb-candidates";
    render(
      <AdminShell mode="fixture">
        <AdminKbCandidatesPage />
      </AdminShell>,
    );

    // OPERATOR 역할에서는 판정 불가 안내
    expect(
      await screen.findByText(/별도 승인자\(APPROVER\)/),
    ).toBeInTheDocument();

    // 역할 전환 (시연 역할 스위치 - 인증 아님)
    fireEvent.change(screen.getAllByRole("combobox")[0], {
      target: { value: "APPROVER" },
    });

    const approve = await screen.findByRole("button", {
      name: "승인하고 ACTIVE 반영",
    });
    // 검수 의견 없이는 승인 불가 (계약 review_comment 필수)
    expect(approve).toBeDisabled();

    fireEvent.change(
      screen.getByRole("textbox", { name: "검수 의견 (필수)" }),
      { target: { value: "정부24 공식 안내 원문 대조 완료" } },
    );
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: "승인하고 ACTIVE 반영" }),
      ).toBeEnabled(),
    );
    fireEvent.click(screen.getByRole("button", { name: "승인하고 ACTIVE 반영" }));

    // 승인 직후 완료형 - ACTIVE 반영 + 스탬프 문구
    await waitFor(() =>
      expect(
        screen.getAllByText("KB 문서가 ACTIVE로 반영되었습니다").length,
      ).toBeGreaterThan(0),
    );
    expect(screen.getByText("ACTIVE")).toBeInTheDocument();
    expect(screen.getByText("다음 시민 답변부터 사용됩니다.")).toBeInTheDocument();
  });
});

describe("fixture admin transport guards (contract invariants)", () => {
  it("blocks self-review, empty comments and MOCK approval", async () => {
    const transport = getFixtureAdminTransport();
    const failure = await curatedFailure();
    await transport.confirmReason(OPERATOR, failure.id, {
      reason: failure.fallback_reason,
    });
    const created = await transport.createCandidate(
      OPERATOR,
      buildCandidateDraft(failure),
    );
    await transport.submitCandidate(OPERATOR, created.id);

    // 자기검수 금지 - 작성자와 같은 actorId
    await expect(
      transport.reviewCandidate(
        { role: "APPROVER", actorId: OPERATOR.actorId },
        created.id,
        { decision: "APPROVED", review_comment: "self" },
      ),
    ).rejects.toThrow();

    // review_comment 공백 금지 (계약 pattern \S)
    await expect(
      transport.reviewCandidate(APPROVER, created.id, {
        decision: "REJECTED",
        review_comment: "   ",
      }),
    ).rejects.toThrow();

    // 공식 출처 초안은 승인 가능
    await expect(
      transport.reviewCandidate(APPROVER, created.id, {
        decision: "APPROVED",
        review_comment: "공식 출처 확인",
      }),
    ).resolves.toEqual({ id: created.id, status: "APPROVED" });
  });

  it("keeps MOCK-origin drafts out of ACTIVE (approval forbidden, rejection allowed)", async () => {
    const transport = getFixtureAdminTransport();
    // 시민 화면에서 근거 부족 폴백 발생 → 실패 큐에 신규 건 적재
    routeDemoAnswer({ question: "전입신고 위임장 서식은 어디서 받나요?" });
    const failures = await transport.listFailedQuestions(OPERATOR);
    const generic = failures.items.find(
      (f) => f.id !== CURATED_ISG_FAILURE_ID && f.candidate_eligible && f.status === "NEW",
    );
    expect(generic).toBeDefined();
    await transport.confirmReason(OPERATOR, generic!.id, {
      reason: generic!.fallback_reason,
    });
    const created = await transport.createCandidate(
      OPERATOR,
      buildCandidateDraft(generic!),
    );
    await transport.submitCandidate(OPERATOR, created.id);

    await expect(
      transport.reviewCandidate(APPROVER, created.id, {
        decision: "APPROVED",
        review_comment: "샘플 데이터 확인",
      }),
    ).rejects.toThrow(/mock candidates/);

    await expect(
      transport.reviewCandidate(APPROVER, created.id, {
        decision: "REJECTED",
        review_comment: "시연용 샘플 - 공식 출처 확인 필요",
      }),
    ).resolves.toEqual({ id: created.id, status: "REJECTED" });
  });

  it("stores personal-lookup fallbacks but never OUT_OF_SCOPE questions", async () => {
    const transport = getFixtureAdminTransport();
    const before = (await transport.listFailedQuestions(OPERATOR)).total;

    routeDemoAnswer({ question: "제 재산세 알려줘" });
    routeDemoAnswer({ question: "오늘 날씨 알려줘" });

    const after = await transport.listFailedQuestions(OPERATOR);
    expect(after.total).toBe(before + 1);
    const newest = after.items[0];
    expect(newest.fallback_reason).toBe("PERSONAL_LOOKUP");
    expect(newest.candidate_eligible).toBe(false);
    // 태성 리뷰 3: PERSONAL_LOOKUP 신규 적재 건은 질문 원문을 싣지 않는다
    expect(newest.masked_question).toBeNull();
  });
});
