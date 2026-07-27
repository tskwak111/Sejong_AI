// @vitest-environment jsdom

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { components } from "../../../../../packages/shared-contracts/src/generated/api";
import AnswerCard from "./AnswerCard";

type SuccessResponse = components["schemas"]["SuccessResponse"];

const response = (sourceId: string): SuccessResponse =>
  ({
    request_id: "11111111-1111-4111-8111-111111111111",
    answer_status: "SUCCESS",
    answer_mode: "TEMPLATE",
    intent: "CERTIFICATE_ISSUANCE",
    confidence: 0.9,
    summary: "공식 안내입니다.",
    procedure_steps: [],
    required_documents: [],
    processing_time: null,
    fee: null,
    department: null,
    sources: [{
      source_id: sourceId,
      title: "공식 증명서 안내",
      url: "https://example.invalid/certificate",
      last_verified_at: "2026-07-20",
    }],
    office: null,
    followup_options: [],
    fallback: null,
    context_token: "signed-certificate-context",
  }) as SuccessResponse;

describe("AnswerCard", () => {
  it("offers exactly two certificate navigation questions only for KB-CERT-01", () => {
    const onRelatedQuestion = vi.fn();
    render(
      <AnswerCard
        response={response("KB-CERT-01")}
        onRelatedQuestion={onRelatedQuestion}
      />,
    );

    const questions = ["주민등록표 열람", "무인민원발급기 이용"];
    expect(
      questions.map((question) => screen.getByRole("button", { name: question })),
    ).toHaveLength(2);
    fireEvent.click(screen.getByRole("button", { name: questions[0] }));
    expect(onRelatedQuestion).toHaveBeenCalledWith(questions[0]);
  });

  it("does not infer certificate navigation questions from intent or title", () => {
    render(<AnswerCard response={response("KB-CERT-02")} />);

    expect(
      screen.queryByRole("button", { name: "주민등록표 열람" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "무인민원발급기 이용" }),
    ).not.toBeInTheDocument();
  });
});
