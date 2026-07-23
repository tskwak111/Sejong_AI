// @vitest-environment jsdom

import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import ChatPage from "./page";

vi.mock("next/navigation", async () => {
  const actual = await vi.importActual<typeof import("next/navigation")>(
    "next/navigation",
  );
  return {
    ...actual,
    useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
    useSearchParams: () => new URLSearchParams(),
  };
});

describe("chat page", () => {
  afterEach(() => {
    delete process.env.CHAT_UI_MODE;
  });

  it("exposes the citizen chat landmarks, composer and privacy warning", () => {
    render(<ChatPage />);

    expect(screen.getByRole("main")).toHaveAttribute("id", "main");
    expect(screen.getByRole("main")).toHaveAttribute("aria-live", "polite");
    expect(screen.getByRole("textbox", { name: "질문 입력" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "전송" })).toBeDisabled();
    expect(screen.getByText("궁금한 민원을 입력해 주세요.")).toBeInTheDocument();
    expect(screen.getByText("개인정보는 입력하지 마세요")).toBeInTheDocument();
    expect(
      screen.getByRole("form", { name: "민원 질문 작성" }),
    ).toBeInTheDocument();
  });
});
