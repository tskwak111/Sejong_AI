// @vitest-environment jsdom

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import FeedbackReasonSheet from "./FeedbackReasonSheet";

function SheetHarness({ onSubmit = vi.fn() }: { onSubmit?: () => void }) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button type="button" onClick={() => setOpen(true)}>
        불만족 사유 열기
      </button>
      <FeedbackReasonSheet
        open={open}
        onClose={() => setOpen(false)}
        onSubmit={onSubmit}
      />
    </>
  );
}

describe("FeedbackReasonSheet keyboard accessibility", () => {
  it("moves focus into the dialog when it opens", async () => {
    render(<SheetHarness />);

    fireEvent.click(screen.getByRole("button", { name: "불만족 사유 열기" }));
    const dialog = screen.getByRole("dialog", { name: "불만족 사유 선택" });

    await waitFor(() =>
      expect(dialog).toContainElement(document.activeElement as HTMLElement | null),
    );
    expect(
      screen.getByRole("radio", { name: "전입·주민등록" }).closest("label"),
    ).toHaveClass("focus-within:outline", "focus-within:outline-primary");
  });

  it("closes on Escape and restores focus to the opener", async () => {
    render(<SheetHarness />);
    const opener = screen.getByRole("button", { name: "불만족 사유 열기" });

    opener.focus();
    fireEvent.click(opener);
    await waitFor(() =>
      expect(screen.getByRole("dialog")).toContainElement(
        document.activeElement as HTMLElement | null,
      ),
    );
    fireEvent.keyDown(document, { key: "Escape" });

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    await waitFor(() => expect(opener).toHaveFocus());
  });

  it("wraps Shift+Tab from the first control to the last enabled control", async () => {
    render(<SheetHarness />);

    fireEvent.click(screen.getByRole("button", { name: "불만족 사유 열기" }));
    const firstControl = screen.getByRole("radio", { name: "전입·주민등록" });
    const closeButton = screen.getByRole("button", { name: "닫기" });
    await waitFor(() => expect(firstControl).toHaveFocus());

    fireEvent.keyDown(document, { key: "Tab", shiftKey: true });

    expect(closeButton).toHaveFocus();
  });

  it("keeps the backward trap after the selected radio changes", async () => {
    render(<SheetHarness />);

    fireEvent.click(screen.getByRole("button", { name: "불만족 사유 열기" }));
    const selectedCategory = screen.getByRole("radio", { name: "대형폐기물" });
    const closeButton = screen.getByRole("button", { name: "닫기" });
    fireEvent.click(selectedCategory);
    selectedCategory.focus();

    fireEvent.keyDown(document, { key: "Tab", shiftKey: true });

    expect(closeButton).toHaveFocus();
  });

  it("wraps Tab from the last enabled control to the first control", async () => {
    render(<SheetHarness />);

    fireEvent.click(screen.getByRole("button", { name: "불만족 사유 열기" }));
    fireEvent.click(screen.getByRole("radio", { name: "전입·주민등록" }));
    fireEvent.click(
      screen.getByRole("radio", { name: "답변 내용이 정확하지 않아요" }),
    );
    const sendButton = screen.getByRole("button", { name: "보내기" });
    sendButton.focus();

    fireEvent.keyDown(document, { key: "Tab" });

    expect(
      screen.getByRole("radio", { name: "전입·주민등록" }),
    ).toHaveFocus();
  });
});
