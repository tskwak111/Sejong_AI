// @vitest-environment jsdom

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { components } from "../../../../../packages/shared-contracts/src/generated/api";

import CandidateAuthoringForm from "./CandidateAuthoringForm";

const FAILURE: components["schemas"]["FailedQuestion"] = {
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

describe("CandidateAuthoringForm validation", () => {
  it("shows the exact approved source hosts and rejects a different https host", () => {
    const onSubmit = vi.fn();
    render(
      <CandidateAuthoringForm
        failure={FAILURE}
        busy={false}
        onCancel={vi.fn()}
        onSubmit={onSubmit}
      />,
    );

    expect(screen.getByText(/허용 출처:/)).toHaveTextContent("www.sjwaste.kr");
    fireEvent.change(screen.getByLabelText("공식 출처 URL"), {
      target: { value: "https://example.com/official" },
    });
    fireEvent.submit(
      screen.getByRole("button", { name: "후보 저장 후 승인 요청" }).closest(
        "form",
      )!,
    );

    expect(screen.getByRole("alert")).toHaveTextContent(
      "허용된 공식 출처 주소를 사용해 주세요",
    );
    expect(onSubmit).not.toHaveBeenCalled();
  });
});
