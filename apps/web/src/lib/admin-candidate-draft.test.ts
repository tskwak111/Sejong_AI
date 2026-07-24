import { describe, expect, it } from "vitest";

import type { components } from "../../../../packages/shared-contracts/src/generated/api";
import { buildActualCandidateDraft } from "./admin-candidate-draft";

type FailedQuestion = components["schemas"]["FailedQuestion"];

const TARGET_FAILURE = {
  id: "10000000-0000-4000-8000-000000000001",
  masked_question: "침대 2인용 프레임 수수료가 얼마예요?",
  intent: "BULKY_WASTE",
  fallback_reason: "INSUFFICIENT_GROUNDING",
  candidate_eligible: true,
  status: "REASON_CONFIRMED",
  created_at: "2026-07-24T00:00:00Z",
  text_expires_at: "2026-08-23T00:00:00Z",
  text_purged_at: null,
} satisfies FailedQuestion;

describe("actual local/private candidate draft", () => {
  it("binds the canonical Q-PM failure to the exact reserved official candidate", () => {
    expect(buildActualCandidateDraft(TARGET_FAILURE)).toEqual({
      failed_question_id: TARGET_FAILURE.id,
      title: "침대 프레임 배출 수수료",
      representative_question: "침대 2인용 프레임 수수료가 얼마예요?",
      category: "BULKY_WASTE",
      answer_summary:
        "공식 품목표의 침대 프레임 수수료는 1인용침대 8,000원, 2인용침대 10,000원으로 표시됩니다.",
      procedure_steps: [
        "공식 품목표에서 침대 프레임의 1인용침대 또는 2인용침대 항목을 확인합니다.",
        "해당 수수료로 공식 배출 절차를 진행합니다.",
      ],
      required_documents: [],
      processing_time: null,
      fee: "1인용침대 8,000원; 2인용침대 10,000원",
      department: "세종특별자치시시설관리공단",
      source_title: "배출항목선택",
      source_url:
        "https://www.sjwaste.kr/wasteApp/appCategoryPopup.do?menuId=MENU00305",
      last_verified_at: "2026-07-18",
      caution:
        "공식 품목표의 1인용침대·2인용침대 항목을 그대로 따릅니다. 매트리스 포함 가격이나 실제 규격을 단정하지 않습니다.",
    });
  });

  it("fails closed instead of labeling an unrelated generated draft as official", () => {
    expect(() =>
      buildActualCandidateDraft({
        ...TARGET_FAILURE,
        masked_question: "다른 근거 부족 질문",
      }),
    ).toThrowError("ACTUAL_CANDIDATE_DRAFT_NOT_APPROVED");
  });
});
