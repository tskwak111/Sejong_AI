// @vitest-environment jsdom

import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import HomePage from "./page";

vi.mock("next/navigation", async () => {
  const actual = await vi.importActual<typeof import("next/navigation")>(
    "next/navigation",
  );
  return {
    ...actual,
    useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  };
});

describe("citizen home page", () => {
  it("presents the service hero with exactly one main heading and the question input", () => {
    render(<HomePage />);

    const mainHeadings = screen.getAllByRole("heading", { level: 1 });
    expect(mainHeadings).toHaveLength(1);
    expect(mainHeadings[0]).toHaveTextContent("궁금한 민원을 물어보세요");
    expect(screen.getByRole("textbox", { name: "질문 입력" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /질문하기/ })).toBeInTheDocument();
  });

  it("lists the four approved service areas from the contract intents", () => {
    render(<HomePage />);

    const scope = screen.getByRole("region", { name: "안내해 드리는 4개 분야" });
    expect(scope).toHaveAttribute("aria-labelledby", "scope-heading");
    for (const label of ["전입·주민등록", "대형폐기물", "증명서 발급", "지방세"]) {
      expect(within(scope).getByText(label)).toBeInTheDocument();
    }
  });

  it("links suggested question chips to the chat screen (SFR-006)", () => {
    render(<HomePage />);

    const chip = screen.getByRole("link", {
      name: "전입신고는 언제까지 해야 하나요?",
    });
    expect(chip).toHaveAttribute(
      "href",
      `/chat?q=${encodeURIComponent("전입신고는 언제까지 해야 하나요?")}`,
    );
    const demo4 = screen.getByRole("link", { name: "제 자동차세 얼마 나왔나요?" });
    expect(demo4).toHaveAttribute(
      "href",
      `/chat?q=${encodeURIComponent("제 자동차세 얼마 나왔나요?")}`,
    );
  });

  it("keeps the always-visible privacy warning under the input (CLAUDE.md §5)", () => {
    render(<HomePage />);

    const form = screen
      .getByRole("textbox", { name: "질문 입력" })
      .closest("form");
    expect(form).not.toBeNull();
    expect(
      within(form as HTMLElement).getByText("개인정보는 입력하지 마세요"),
    ).toBeInTheDocument();
  });
});
