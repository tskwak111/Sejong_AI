// @vitest-environment jsdom

import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type {
  ChatRequest,
  ChatResponse,
  ChatTransport,
  Office,
} from "../../lib/chat-api";
import { ChatTransportError } from "../../lib/chat-api";
import {
  consumePendingQuestion,
  setPendingQuestion,
} from "../../lib/pending-question";

import ChatScreen from "./chat-screen";

vi.mock("next/navigation", async () => {
  const actual = await vi.importActual<typeof import("next/navigation")>(
    "next/navigation",
  );
  return {
    ...actual,
    useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  };
});

const OFFICE = {
  id: "office-001",
  region: "아름동",
  office_name: "아름동 행정복지센터",
  address: "세종특별자치시 보듬3로 114",
  phone: "044-301-6361",
  opening_hours: "평일 09:00~18:00",
  map_url: "https://example.invalid/official/office-map",
  source_title: "세종특별자치시 공식 안내",
  source_url: "https://example.invalid/official/office",
  last_verified_at: "2026-07-20",
} satisfies Office;

const SUCCESS_RESPONSE = {
  request_id: "11111111-1111-4111-8111-111111111111",
  answer_status: "SUCCESS",
  intent: "MOVE_IN_RESIDENT_REGISTRATION",
  confidence: 0.96,
  summary: "전입신고는 전입한 날부터 14일 이내에 해요.",
  procedure_steps: ["신고서를 작성해요.", "행정복지센터에 제출해요."],
  required_documents: ["신분증"],
  processing_time: "즉시",
  fee: "없음",
  department: "주민등록 담당",
  sources: [
    {
      source_id: "source-001",
      title: "세종특별자치시 전입신고 안내",
      url: "https://example.invalid/official/move-in",
      last_verified_at: "2026-07-20",
    },
  ],
  office: OFFICE,
  context_token: "signed-context-one",
} satisfies ChatResponse;

function transportWith(send: ChatTransport["send"]): ChatTransport {
  return { send };
}

function ask(question: string) {
  fireEvent.change(screen.getByRole("textbox", { name: "질문 입력" }), {
    target: { value: question },
  });
  fireEvent.click(screen.getByRole("button", { name: "전송" }));
}

afterEach(() => {
  vi.restoreAllMocks();
  consumePendingQuestion(); // 테스트 간 탭 메모리 초기화
});

describe("citizen chat screen", () => {
  it("auto-sends the home-screen question from tab memory, consuming it once (태성 리뷰 1)", async () => {
    setPendingQuestion("전입신고는 언제까지 해야 하나요?");
    const send = vi.fn().mockResolvedValue(SUCCESS_RESPONSE);
    render(<ChatScreen transport={transportWith(send)} />);

    await waitFor(() => expect(send).toHaveBeenCalledTimes(1));
    expect((send.mock.calls[0][0] as ChatRequest).question).toBe(
      "전입신고는 언제까지 해야 하나요?",
    );
    // 1회성 소비 - URL은 물론 탭 메모리에도 질문이 남지 않는다
    expect(consumePendingQuestion()).toBeNull();
    expect(window.location.search).toBe("");
  });

  it("renders a successful answer with source, office metadata and the generated request shape", async () => {
    const send = vi.fn().mockResolvedValue(SUCCESS_RESPONSE);
    render(
      <ChatScreen
        transport={transportWith(send)}
        createIdempotencyKey={() => "99999999-9999-4999-8999-999999999999"}
      />,
    );

    ask("이사했는데 전입신고 어떻게 해요?");

    expect(
      await screen.findByText((_, node) =>
        node?.textContent === SUCCESS_RESPONSE.summary &&
        node?.tagName === "P",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("신분증")).toBeInTheDocument();
    const sourceLink = screen.getByRole("link", { name: /원문 보기/ });
    expect(sourceLink).toHaveAttribute("href", SUCCESS_RESPONSE.sources[0].url);
    expect(screen.getByText(SUCCESS_RESPONSE.sources[0].title)).toBeInTheDocument();
    expect(screen.getByText("2026-07-20 확인 기준")).toBeInTheDocument();
    expect(screen.getByText(OFFICE.office_name)).toBeInTheDocument();
    expect(screen.getByText(OFFICE.address)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: OFFICE.phone })).toBeInTheDocument();
    expect(send).toHaveBeenCalledWith(
      {
        question: "이사했는데 전입신고 어떻게 해요?",
        selected_region: null,
        simple_language: true,
        context_token: null,
      },
      { idempotencyKey: "99999999-9999-4999-8999-999999999999" },
    );
  });

  it("keeps follow-up context only in React memory and sends it with the selected option", async () => {
    const followup = {
      request_id: "22222222-2222-4222-8222-222222222222",
      answer_status: "FOLLOWUP",
      intent: "UNKNOWN",
      sources: [],
      followup_options: ["전입신고는 언제까지 해야 하나요?", "주민등록등본은 어떻게 발급받나요?"],
      office: null,
      context_token: "signed-followup-context",
    } satisfies ChatResponse;
    const send = vi.fn().mockResolvedValueOnce(followup).mockResolvedValueOnce(SUCCESS_RESPONSE);
    const localStorageSpy = vi.spyOn(Storage.prototype, "setItem");
    render(<ChatScreen transport={transportWith(send)} />);

    ask("신고하고 싶어요.");
    const option = await screen.findByRole("button", {
      name: "전입신고는 언제까지 해야 하나요?",
    });
    fireEvent.click(option);

    await waitFor(() => expect(send).toHaveBeenCalledTimes(2));
    expect(send.mock.calls[1][0]).toEqual({
      question: "전입신고는 언제까지 해야 하나요?",
      selected_region: null,
      simple_language: true,
      context_token: "signed-followup-context",
    } satisfies ChatRequest);
    expect(localStorageSpy).not.toHaveBeenCalled();
    expect(window.sessionStorage.length).toBe(0);
    expect(document.cookie).toBe("");
  });

  it("promotes a region-name follow-up option to selected_region and resends the original question", async () => {
    const regionFollowup = {
      request_id: "44444444-4444-4444-8444-444444444444",
      answer_status: "FOLLOWUP",
      intent: "BULKY_WASTE",
      sources: [],
      followup_options: ["아름동", "도담동", "조치원읍"],
      office: null,
      context_token: "signed-region-context",
    } satisfies ChatResponse;
    const success = {
      ...SUCCESS_RESPONSE,
      intent: "BULKY_WASTE",
      request_id: "55555555-5555-4555-8555-555555555555",
    } satisfies ChatResponse;
    const send = vi.fn().mockResolvedValueOnce(regionFollowup).mockResolvedValueOnce(success);
    render(<ChatScreen transport={transportWith(send)} />);

    ask("대형폐기물은 언제 내놓나요?");
    fireEvent.click(await screen.findByRole("button", { name: "아름동" }));

    await waitFor(() => expect(send).toHaveBeenCalledTimes(2));
    expect(send.mock.calls[1][0]).toEqual({
      question: "대형폐기물은 언제 내놓나요?",
      selected_region: "아름동",
      simple_language: true,
      context_token: "signed-region-context",
    } satisfies ChatRequest);
    // 사용자 말풍선에는 지역 선택이 자연어로 남는다
    expect(await screen.findByText("아름동에 살아요")).toBeInTheDocument();
  });

  it.each([
    ["INSUFFICIENT_GROUNDING", true, "LOCAL_TAX_GENERAL"],
    ["PERSONAL_LOOKUP", false, "UNKNOWN"],
    ["LEGAL_JUDGMENT", false, "UNKNOWN"],
    ["OUT_OF_SCOPE", false, "OUT_OF_SCOPE"],
  ] as const)(
    "renders the %s fallback title, message and no source strip",
    async (reason, eligible, intent) => {
      const response = {
        request_id: "33333333-3333-4333-8333-333333333333",
        answer_status: "FALLBACK",
        intent,
        confidence: null,
        sources: [],
        fallback: {
          reason,
          title: `${reason} 안내 제목`,
          message: "안전하게 연결해 드립니다.",
          candidate_eligible: eligible,
          office: null,
        },
        context_token: null,
      } as ChatResponse;
      render(<ChatScreen transport={transportWith(vi.fn().mockResolvedValue(response))} />);

      ask("테스트 질문");

      const title = await screen.findByText(`${reason} 안내 제목`);
      const article = title.closest("article");
      expect(article).not.toBeNull();
      expect(
        within(article as HTMLElement).getByText("안전하게 연결해 드립니다."),
      ).toBeInTheDocument();
      expect(screen.queryByText("공식 출처 확인")).not.toBeInTheDocument();
      expect(screen.getByRole("main")).toHaveAttribute("aria-live", "polite");
    },
  );

  it("renders the PRIVACY_UNRESOLVED fallback with its fixed contract copy", async () => {
    const response = {
      request_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
      answer_status: "FALLBACK",
      intent: "UNKNOWN",
      confidence: null,
      sources: [],
      fallback: {
        reason: "PRIVACY_UNRESOLVED",
        title: "개인정보를 안전하게 처리하지 못했어요",
        message: "개인정보를 빼거나 표현을 바꿔서 다시 질문해 주세요.",
        next_actions: ["이름, 주소, 전화번호, 접수번호 등을 적지 마세요."],
        candidate_eligible: false,
        office: null,
      },
      context_token: null,
    } as ChatResponse;
    render(<ChatScreen transport={transportWith(vi.fn().mockResolvedValue(response))} />);

    ask("010-1234-5678 제 접수 내역 알려줘");

    expect(
      await screen.findByText("개인정보를 안전하게 처리하지 못했어요"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("개인정보를 빼거나 표현을 바꿔서 다시 질문해 주세요."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("이름, 주소, 전화번호, 접수번호 등을 적지 마세요."),
    ).toBeInTheDocument();
  });

  it("prevents duplicate submission while a request is loading", async () => {
    let resolveResponse: ((response: ChatResponse) => void) | undefined;
    const pending = new Promise<ChatResponse>((resolve) => {
      resolveResponse = resolve;
    });
    const send = vi.fn().mockReturnValue(pending);
    render(<ChatScreen transport={transportWith(send)} />);

    ask("전입신고 알려줘");
    const submit = screen.getByRole("button", { name: "답변 확인 중" });
    expect(submit).toBeDisabled();
    fireEvent.click(submit);
    expect(send).toHaveBeenCalledTimes(1);
    expect(
      screen.getByRole("status", { name: "공식 자료에서 확인하고 있어요" }),
    ).toBeInTheDocument();

    resolveResponse?.(SUCCESS_RESPONSE);
    expect(
      await screen.findByText((_, node) =>
        node?.textContent === SUCCESS_RESPONSE.summary && node?.tagName === "P",
      ),
    ).toBeInTheDocument();
  });

  it("shows a value-free error and retries the same in-memory draft with the same idempotency key", async () => {
    const firstKey = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
    const secondKey = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
    const createIdempotencyKey = vi.fn()
      .mockReturnValueOnce(firstKey)
      .mockReturnValueOnce(secondKey);
    const secondResponse = {
      ...SUCCESS_RESPONSE,
      request_id: "77777777-7777-4777-8777-777777777777",
    } satisfies ChatResponse;
    const send = vi.fn()
      .mockRejectedValueOnce(new Error("raw upstream payload must stay hidden"))
      .mockResolvedValueOnce(SUCCESS_RESPONSE)
      .mockResolvedValueOnce(secondResponse);
    render(
      <ChatScreen
        transport={transportWith(send)}
        createIdempotencyKey={createIdempotencyKey}
      />,
    );

    ask("이사했는데 신고를 알려줘");

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "지금은 안전한 답변을 만들 수 없어요.",
    );
    expect(screen.queryByText(/raw upstream/)).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "다시 시도" }));
    await waitFor(() => expect(send).toHaveBeenCalledTimes(2));

    ask("새 질문");
    await waitFor(() => expect(send).toHaveBeenCalledTimes(3));

    expect(createIdempotencyKey).toHaveBeenCalledTimes(2);
    expect(send.mock.calls[0][1]).toEqual({ idempotencyKey: firstKey });
    expect(send.mock.calls[1][1]).toEqual({ idempotencyKey: firstKey });
    expect(send.mock.calls[2][1]).toEqual({ idempotencyKey: secondKey });
  });

  it("does not offer retry for a non-retryable validation error", async () => {
    const send = vi.fn().mockRejectedValue(new ChatTransportError(422, false));
    render(<ChatScreen transport={transportWith(send)} />);

    ask("잘못된 요청");

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "입력 내용을 확인한 뒤 새 질문을 보내 주세요.",
    );
    expect(screen.queryByRole("button", { name: "다시 시도" })).not.toBeInTheDocument();
  });

  it("resets the context token after a FALLBACK response (contract: token is null)", async () => {
    const fallback = {
      request_id: "66666666-6666-4666-8666-666666666666",
      answer_status: "FALLBACK",
      intent: "OUT_OF_SCOPE",
      confidence: null,
      sources: [],
      fallback: {
        reason: "OUT_OF_SCOPE",
        title: "다른 창구 안내",
        message: "다른 창구로 연결해 드립니다.",
        candidate_eligible: false,
        office: null,
      },
      context_token: null,
    } as ChatResponse;
    const send = vi.fn()
      .mockResolvedValueOnce(SUCCESS_RESPONSE)
      .mockResolvedValueOnce(fallback)
      .mockResolvedValueOnce(SUCCESS_RESPONSE);
    render(<ChatScreen transport={transportWith(send)} />);

    ask("전입신고 알려줘");
    await waitFor(() => expect(send).toHaveBeenCalledTimes(1));
    ask("범위 밖 질문");
    await waitFor(() => expect(send).toHaveBeenCalledTimes(2));
    ask("전입신고 다시 알려줘");
    await waitFor(() => expect(send).toHaveBeenCalledTimes(3));

    expect((send.mock.calls[1][0] as ChatRequest).context_token).toBe(
      "signed-context-one",
    );
    expect((send.mock.calls[2][0] as ChatRequest).context_token).toBeNull();
  });
});
