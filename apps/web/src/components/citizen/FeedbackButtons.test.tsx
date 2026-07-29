// @vitest-environment jsdom

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type {
  FeedbackCreateResponse,
  FeedbackTransport,
} from "@/lib/feedback-api";
import FeedbackButtons from "./FeedbackButtons";

const REQUEST_ID = "11111111-1111-4111-8111-111111111111";

describe("FeedbackButtons", () => {
  it("shows thanks only after satisfied feedback is stored", async () => {
    let resolveRecord: (() => void) | undefined;
    const transport: FeedbackTransport = {
      record: vi.fn(
        () =>
          new Promise<FeedbackCreateResponse>((resolve) => {
            resolveRecord = () =>
              resolve({
                request_id: REQUEST_ID,
                status: "RECORDED",
                detail_status: "NOT_PROVIDED",
              });
          }),
      ),
    };
    render(<FeedbackButtons requestId={REQUEST_ID} transport={transport} />);

    fireEvent.click(screen.getByRole("button", { name: "만족" }));
    expect(screen.getByRole("button", { name: "저장 중" })).toBeDisabled();
    expect(screen.queryByText("의견을 선택해 주셔서 감사합니다")).toBeNull();

    resolveRecord?.();
    await waitFor(() =>
      expect(
        screen.getByText("의견을 선택해 주셔서 감사합니다"),
      ).toBeInTheDocument(),
    );
    expect(transport.record).toHaveBeenCalledWith({
      request_id: REQUEST_ID,
      rating: "SATISFIED",
      category: null,
      reason_code: null,
      detail: null,
    });
  });

  it("keeps the controls available when storage fails", async () => {
    const transport: FeedbackTransport = {
      record: vi.fn().mockRejectedValue(new Error("offline")),
    };
    render(<FeedbackButtons requestId={REQUEST_ID} transport={transport} />);

    fireEvent.click(screen.getByRole("button", { name: "만족" }));

    expect(
      await screen.findByRole("alert"),
    ).toHaveTextContent("의견을 저장하지 못했어요");
    expect(screen.getByRole("button", { name: "만족" })).toBeEnabled();
  });
});
