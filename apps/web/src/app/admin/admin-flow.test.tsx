// @vitest-environment jsdom

/**
 * 이음센터 핵심 루프 테스트 - fixture는 UI 개발·상태 확인 도구다
 * (Q-PM-DEMO-001·Q-MVP-002/D-059):
 * 실패 질문 큐(NEW) → 사유 확정(REASON_CONFIRMED) → 근거 부족 건만 KB 후보
 * 생성(DRAFTED→PENDING_APPROVAL)까지가 fixture 확인 범위다.
 * 저장 정책: INSUFFICIENT_GROUNDING만 행 생성, PERSONAL_LOOKUP·LEGAL_JUDGMENT·
 * OUT_OF_SCOPE는 완전 미저장. fixture 후보는 전부 MOCK이며 승인·반려 판정과
 * ACTIVE 전환은 actual 경로 전용이다.
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

const ISG_QUESTION = "침대 2인용 프레임은 배출 수수료가 얼마인가요?";

async function curatedFailure() {
  const transport = getFixtureAdminTransport();
  const list = await transport.listFailedQuestions(OPERATOR);
  const failure = list.items.find((f) => f.id === CURATED_ISG_FAILURE_ID);
  if (!failure) throw new Error("curated fixture missing");
  return failure;
}

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

beforeEach(() => {
  resetDemoStore();
  mockPathname = "/admin/failures";
});

describe("failures screen (fixture)", () => {
  it("renders grounding and purged rows - no PERSONAL_LOOKUP row exists (D-059)", async () => {
    render(
      <AdminShell mode="fixture">
        <AdminFailuresPage />
      </AdminShell>,
    );

    expect((await screen.findAllByText(ISG_QUESTION)).length).toBeGreaterThan(0);
    // Q-MVP-002/D-059: PERSONAL_LOOKUP은 완전 미저장 - 초기 fixture에도 없다
    expect(
      screen.queryByText("제 자동차세 얼마 나왔나요?"),
    ).not.toBeInTheDocument();
    // 30일 파기 행 - NULL이어도 깨지지 않는다 (테이블 + 모바일 카드 각 1회)
    expect(screen.getAllByText(/보관 기간 경과/).length).toBeGreaterThan(0);
    // 저장 사유 필터는 계약 3종 + 전체 (OUT_OF_SCOPE 필터 없음)
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
    await screen.findAllByText(ISG_QUESTION);

    // NEW 행(근거 부족) - 사유 확정 버튼 노출 (테이블/모바일 중복 렌더)
    const confirmButtons = screen.getAllByRole("button", { name: "사유 확정" });
    expect(confirmButtons.length).toBeGreaterThan(0);

    // 근거 부족 건 사유 확정 → KB 후보 생성 버튼 등장
    const isgRow = screen
      .getAllByText(ISG_QUESTION)[0]
      .closest("tr, article") as HTMLElement;
    fireEvent.click(isgRow.querySelector("button") as HTMLButtonElement);

    await waitFor(() =>
      expect(screen.getAllByText("사유가 확정되었습니다").length).toBeGreaterThan(0),
    );
    const createButtons = await screen.findAllByRole("button", {
      name: "KB 후보 생성",
    });
    fireEvent.click(createButtons[0]);

    expect(
      await screen.findByRole("heading", { name: "공식 KB 후보 작성" }),
    ).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("제목"), {
      target: { value: "침대 프레임 배출 수수료" },
    });
    fireEvent.change(screen.getByLabelText("답변 요약"), {
      target: { value: "공식 품목표의 수수료를 안내합니다." },
    });
    fireEvent.change(screen.getByLabelText("처리 절차 (한 줄에 한 단계)"), {
      target: { value: "공식 품목표를 확인합니다.\n배출 절차를 진행합니다." },
    });
    fireEvent.change(screen.getByLabelText("담당 부서"), {
      target: { value: "세종특별자치시시설관리공단" },
    });
    fireEvent.change(screen.getByLabelText("공식 출처명"), {
      target: { value: "배출항목선택" },
    });
    fireEvent.change(screen.getByLabelText("공식 출처 URL"), {
      target: { value: "https://www.sjwaste.kr/wasteApp/appCategoryPopup.do" },
    });
    fireEvent.change(screen.getByLabelText("출처 확인일"), {
      target: { value: "2026-07-27" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "후보 저장 후 승인 요청" }),
    );

    await waitFor(() =>
      expect(
        screen.getAllByText(/운영자가 작성한 KB 후보가 승인 요청되었습니다/).length,
      ).toBeGreaterThan(0),
    );
    // 승인 화면 이동 배너
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
  it("keeps approve/reject disabled with the lock reason - judgement is actual-only (Q-PM-DEMO-001)", async () => {
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

    // fixture 판정 비활성 - 승인·반려 버튼 모두 비활성 + 사유 툴팁·캡션
    const approve = await screen.findByRole("button", {
      name: "승인하고 ACTIVE 반영",
    });
    const reject = screen.getByRole("button", { name: "반려" });
    expect(approve).toBeDisabled();
    expect(reject).toBeDisabled();
    expect(approve.getAttribute("title")).toMatch(/판정을 지원하지 않습니다/);
    expect(reject.getAttribute("title")).toMatch(/판정을 지원하지 않습니다/);
    expect(
      screen.getByRole("textbox", { name: "검수 의견 (필수)" }),
    ).toBeDisabled();
    expect(
      screen.getByText(/승인·반려 판정을 지원하지 않습니다/),
    ).toBeInTheDocument();
    // ACTIVE 전환 완료형이 나타나지 않는다
    expect(
      screen.queryByText("KB 문서가 ACTIVE로 반영되었습니다"),
    ).not.toBeInTheDocument();
  });
});

describe("fixture admin transport guards (Q-PM-DEMO-001·Q-MVP-002/D-059)", () => {
  it("stores only INSUFFICIENT_GROUNDING - PERSONAL_LOOKUP and OUT_OF_SCOPE leave zero rows", async () => {
    const transport = getFixtureAdminTransport();
    const before = (await transport.listFailedQuestions(OPERATOR)).total;

    routeDemoAnswer({ question: "제 자동차세 얼마 나왔나요?" });
    routeDemoAnswer({ question: "오늘 날씨 알려줘" });

    const after = await transport.listFailedQuestions(OPERATOR);
    expect(after.total).toBe(before);
    expect(
      after.items.filter((f) => f.fallback_reason === "PERSONAL_LOOKUP"),
    ).toHaveLength(0);

    // 근거 부족만 행을 만든다
    routeDemoAnswer({ question: "침대 프레임 배출 수수료 알려줘" });
    const withIsg = await transport.listFailedQuestions(OPERATOR);
    expect(withIsg.total).toBe(before + 1);
    expect(withIsg.items[0].fallback_reason).toBe("INSUFFICIENT_GROUNDING");
    expect(withIsg.items[0].candidate_eligible).toBe(true);
  });

  it("creates fixture candidates as MOCK only and never transitions them to ACTIVE", async () => {
    const transport = getFixtureAdminTransport();
    const createdId = await seedPendingCuratedCandidate();

    // fixture 강등: OFFICIAL 판정 로직 없음 - 전부 시연용 샘플(MOCK)
    const list = await transport.listCandidates(OPERATOR);
    const candidate = list.items.find((c) => c.id === createdId);
    expect(candidate?.data_origin).toBe("MOCK");
    expect(candidate?.status).toBe("PENDING_APPROVAL");

    // 승인·반려 어느 판정도 불가 → ACTIVE 전환 불가
    await expect(
      transport.reviewCandidate(APPROVER, createdId, {
        decision: "APPROVED",
        review_comment: "샘플 확인",
      }),
    ).rejects.toThrow(/cannot be reviewed/);
    await expect(
      transport.reviewCandidate(APPROVER, createdId, {
        decision: "REJECTED",
        review_comment: "샘플 확인",
      }),
    ).rejects.toThrow(/cannot be reviewed/);

    const afterReview = await transport.listCandidates(OPERATOR);
    const untouched = afterReview.items.find((c) => c.id === createdId);
    expect(untouched?.status).toBe("PENDING_APPROVAL");
    expect(untouched?.activated_kb_id).toBeNull();
    expect(untouched?.approved_at).toBeNull();
  });
});
