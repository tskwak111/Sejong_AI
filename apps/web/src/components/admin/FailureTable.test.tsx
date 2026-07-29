// @vitest-environment jsdom

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { components } from "../../../../../packages/shared-contracts/src/generated/api";

import FailureTable from "./FailureTable";

type FailedQuestion = components["schemas"]["FailedQuestion"];
type KBCandidateSummary = components["schemas"]["KBCandidateSummary"];

const FAILURE: FailedQuestion = {
  id: "11111111-1111-4111-8111-111111111111",
  masked_question: "마스킹된 질문",
  intent: "BULKY_WASTE",
  fallback_reason: "INSUFFICIENT_GROUNDING",
  candidate_eligible: true,
  status: "REASON_CONFIRMED",
  created_at: "2026-07-29T00:00:00Z",
  text_expires_at: "2026-08-28T00:00:00Z",
  text_purged_at: null,
};

const DRAFT: KBCandidateSummary = {
  id: "22222222-2222-4222-8222-222222222222",
  failed_question_id: FAILURE.id,
  title: "저장된 후보",
  representative_question: "대표 질문",
  data_origin: "OFFICIAL",
  category: "BULKY_WASTE",
  answer_summary: "요약",
  procedure_steps: [],
  required_documents: [],
  processing_time: null,
  fee: null,
  department: "담당 부서",
  source_title: "공식 출처",
  source_url: "https://example.go.kr",
  last_verified_at: "2026-07-29",
  caution: null,
  status: "DRAFTED",
  created_by: "OPERATOR-LOCAL-001",
  reviewed_by: null,
  review_comment: null,
  approved_at: null,
  activated_kb_id: null,
  created_at: "2026-07-29T00:00:00Z",
  updated_at: "2026-07-29T00:00:00Z",
};

describe("FailureTable candidate recovery", () => {
  it("offers submit retry when a saved candidate is still DRAFTED", () => {
    const onSubmitDraft = vi.fn();
    render(
      <FailureTable
        items={[FAILURE]}
        candidateByFailureId={new Map([[FAILURE.id, DRAFT]])}
        busyId={null}
        canOperate
        onConfirmReason={vi.fn()}
        onCreateDraft={vi.fn()}
        onSubmitDraft={onSubmitDraft}
      />,
    );

    const buttons = screen.getAllByRole("button", { name: "승인 요청 다시 시도" });
    fireEvent.click(buttons[0]);

    expect(onSubmitDraft).toHaveBeenCalledWith(DRAFT.id, DRAFT.title);
  });
});
