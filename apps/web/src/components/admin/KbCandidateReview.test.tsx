// @vitest-environment jsdom

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { components } from "../../../../../packages/shared-contracts/src/generated/api";
import KbCandidateReview from "./KbCandidateReview";

type KBCandidateSummary = components["schemas"]["KBCandidateSummary"];

const OFFICIAL_PENDING_CANDIDATE = {
  id: "20000000-0000-4000-8000-000000000001",
  failed_question_id: "10000000-0000-4000-8000-000000000001",
  title: "침대 프레임 배출 수수료",
  representative_question: "침대 2인용 프레임 수수료가 얼마예요?",
  data_origin: "OFFICIAL",
  category: "BULKY_WASTE",
  answer_summary:
    "공식 품목표의 침대 프레임 수수료는 규격에 따라 다릅니다.",
  procedure_steps: ["공식 품목표를 확인합니다."],
  required_documents: [],
  processing_time: null,
  fee: "2인용침대 10,000원",
  department: "세종특별자치시시설관리공단",
  source_title: "배출항목선택",
  source_url:
    "https://www.sjwaste.kr/wasteApp/appCategoryPopup.do?menuId=MENU00305",
  last_verified_at: "2026-07-18",
  caution: null,
  status: "PENDING_APPROVAL",
  created_by: "OPERATOR-LOCAL-001",
  reviewed_by: null,
  review_comment: null,
  approved_at: null,
  activated_kb_id: null,
  created_at: "2026-07-24T00:00:00Z",
  updated_at: "2026-07-24T00:00:00Z",
} satisfies KBCandidateSummary;

describe("KbCandidateReview approval gate", () => {
  it("requires all three verification checks in addition to an approver comment", () => {
    const onReview = vi.fn();
    render(
      <KbCandidateReview
        candidate={OFFICIAL_PENDING_CANDIDATE}
        actor={{ role: "APPROVER", actorId: "PM-LOCAL-001" }}
        busy={false}
        justApproved={false}
        onReview={onReview}
        onNext={vi.fn()}
      />,
    );

    fireEvent.change(
      screen.getByRole("textbox", { name: "검수 의견 (필수)" }),
      { target: { value: "공식 출처 원문 대조 완료" } },
    );
    const approve = screen.getByRole("button", {
      name: "승인하고 ACTIVE 반영",
    });
    expect(approve).toBeDisabled();

    const checks = screen.getAllByRole("checkbox");
    fireEvent.click(checks[0]);
    fireEvent.click(checks[1]);
    expect(approve).toBeDisabled();

    fireEvent.click(checks[2]);
    expect(approve).toBeEnabled();

    fireEvent.click(approve);
    expect(onReview).toHaveBeenCalledWith(
      OFFICIAL_PENDING_CANDIDATE.id,
      "APPROVED",
      "공식 출처 원문 대조 완료",
    );
  });
});
