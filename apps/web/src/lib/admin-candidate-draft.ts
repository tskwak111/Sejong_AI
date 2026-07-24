import type { components } from "../../../../packages/shared-contracts/src/generated/api";

type FailedQuestion = components["schemas"]["FailedQuestion"];
type KBCandidateCreate = components["schemas"]["KBCandidateCreate"];

const RESERVED_QUESTION = "침대 2인용 프레임 수수료가 얼마예요?";

/**
 * Build the one PM-approved local/private candidate that the backend binds to
 * public ID KB-WASTE-03. Actual mode must not promote fixture or improvised
 * content as OFFICIAL.
 */
export function buildActualCandidateDraft(
  failure: FailedQuestion,
): KBCandidateCreate {
  if (
    failure.masked_question !== RESERVED_QUESTION ||
    failure.intent !== "BULKY_WASTE" ||
    failure.fallback_reason !== "INSUFFICIENT_GROUNDING" ||
    failure.status !== "REASON_CONFIRMED" ||
    !failure.candidate_eligible
  ) {
    throw new Error("ACTUAL_CANDIDATE_DRAFT_NOT_APPROVED");
  }

  return {
    failed_question_id: failure.id,
    title: "침대 프레임 배출 수수료",
    representative_question: RESERVED_QUESTION,
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
  };
}
