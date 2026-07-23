// @vitest-environment jsdom

import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import HomePage from "./page";
import { consumePendingQuestion } from "../lib/pending-question";

const { pushMock } = vi.hoisted(() => ({ pushMock: vi.fn() }));

vi.mock("next/navigation", async () => {
  const actual = await vi.importActual<typeof import("next/navigation")>(
    "next/navigation",
  );
  return {
    ...actual,
    useRouter: () => ({ push: pushMock, replace: vi.fn() }),
  };
});

afterEach(() => {
  pushMock.mockReset();
  consumePendingQuestion(); // 테스트 간 탭 메모리 초기화
  delete process.env.CHAT_UI_MODE;
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

  it("hands suggested question chips to chat via tab memory, never the URL (태성 리뷰 1)", () => {
    render(<HomePage />);

    const chip = screen.getByRole("link", {
      name: "전입신고는 언제까지 해야 하나요?",
    });
    // 질문 원문이 href(URL·히스토리·서버 로그)에 남지 않는다
    expect(chip).toHaveAttribute("href", "/chat");
    chip.addEventListener("click", (event) => event.preventDefault());
    fireEvent.click(chip);
    expect(consumePendingQuestion()).toBe("전입신고는 언제까지 해야 하나요?");

    const demo4 = screen.getByRole("link", { name: "제 자동차세 얼마 나왔나요?" });
    expect(demo4).toHaveAttribute("href", "/chat");
  });

  it("submits the typed question through tab memory and navigates without a query string", () => {
    render(<HomePage />);

    fireEvent.change(screen.getByRole("textbox", { name: "질문 입력" }), {
      target: { value: "전입신고는 언제까지 해야 하나요?" },
    });
    fireEvent.click(screen.getByRole("button", { name: /질문하기/ }));

    expect(pushMock).toHaveBeenCalledWith("/chat");
    expect(consumePendingQuestion()).toBe("전입신고는 언제까지 해야 하나요?");
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

  it("shows the fixture sample banner only when fixture mode is explicit (태성 리뷰 2)", () => {
    render(<HomePage />);
    expect(
      screen.queryByText("시연용 샘플 — 공식 데이터 아님"),
    ).not.toBeInTheDocument();
  });
});
