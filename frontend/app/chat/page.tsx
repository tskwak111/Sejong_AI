"use client";

/**
 * 시민 대화 화면 - CLAUDE.md §4 응답 4가지 상태 전부 처리, DESIGN.md v3 §6·§8.
 * 프레임: 헤더(뒤로가기 44px + 워드마크, sticky) + 680px 대화 컬럼 +
 * 하단 sticky 입력바(개인정보 경고 한 줄 위). 사용자 말풍선은 primary 채움,
 * 반경 16/16/4/16. 대화 내용은 React state로만 유지, 브라우저 스토리지 저장
 * 금지 (§9). 새 답변은 aria-live="polite" 영역으로 스크린리더에 알린다.
 */
import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import type { ChatResponse } from "@/types/api";
import { askQuestion, resetConversation } from "@/lib/api";
import { ChatHeader, NoticeBanner } from "@/components/citizen/PageChrome";
import AnswerCard from "@/components/citizen/AnswerCard";
import FollowupCard from "@/components/citizen/FollowupCard";
import FallbackCard from "@/components/citizen/FallbackCard";
import LoadingSkeleton from "@/components/citizen/LoadingSkeleton";
import PrivacyNotice from "@/components/citizen/PrivacyNotice";

interface UserMessage {
  role: "user";
  id: string;
  text: string;
}
interface BotMessage {
  role: "bot";
  id: string;
  response: ChatResponse;
  /** 이 응답을 만든 질문/지역 - 재시도·동 변경에 사용 */
  question: string;
  region?: string;
}
type Message = UserMessage | BotMessage;

function ChatScreen() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialQuestion = searchParams.get("q") ?? "";
  // context_token 만료 강제 발동 (시연·검증 전용, 기본 비활성 - CLAUDE.md §9)
  const forceExpire = searchParams.get("demo_expire") === "1";

  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [input, setInput] = useState("");
  const [expired, setExpired] = useState(false);
  const idRef = useRef(0);
  const bottomRef = useRef<HTMLDivElement>(null);
  const askedInitial = useRef(false);

  const nextId = () => `msg-${++idRef.current}`;

  const ask = useCallback(
    async (
      question: string,
      opts?: { region?: string; displayText?: string },
    ) => {
      const display = opts?.displayText ?? question;
      setMessages((prev) => [
        ...prev,
        { role: "user", id: nextId(), text: display },
      ]);
      setLoading(true);
      try {
        const response = await askQuestion(question, {
          region: opts?.region,
          forceExpire,
        });
        // 토큰 만료 → 탭 메모리의 대화 내용 초기화 + 만료 안내 UI (§9)
        if (
          response.result_type === "ERROR" &&
          response.error_code === "CONTEXT_EXPIRED"
        ) {
          setMessages([]);
          setInput("");
          setExpired(true);
          return;
        }
        setMessages((prev) => [
          ...prev,
          {
            role: "bot",
            id: nextId(),
            response,
            question,
            region: opts?.region,
          },
        ]);
      } finally {
        setLoading(false);
      }
    },
    [forceExpire],
  );

  /** 만료 안내의 "새 대화 시작" - 토큰 재발급 + 대화 초기화 + 쿼리 제거 */
  const startNewConversation = () => {
    void resetConversation();
    setMessages([]);
    setInput("");
    setExpired(false);
    askedInitial.current = true; // 초기 질문 재전송 방지
    router.replace("/chat");
  };

  // 첫 화면에서 넘어온 질문 자동 전송
  useEffect(() => {
    if (initialQuestion && !askedInitial.current) {
      askedInitial.current = true;
      void ask(initialQuestion);
    }
  }, [initialQuestion, ask]);

  useEffect(() => {
    // §12: prefers-reduced-motion 존중 - smooth 스크롤도 모션이다
    const reduced = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    bottomRef.current?.scrollIntoView({
      behavior: reduced ? "auto" : "smooth",
    });
  }, [messages, loading]);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const q = input.trim();
    if (!q || loading || expired) return;
    setInput("");
    void ask(q);
  };

  return (
    <div className="flex min-h-screen flex-col bg-bg">
      {/* 공지 배너 - 시민 전 페이지 최상단 (대화 화면 개정 1) */}
      <NoticeBanner />
      <ChatHeader />

      {/* 대화 컬럼 - 데스크톱 680px 고정 (§4-2). 새 답변을 스크린리더에 알린다 */}
      <main
        id="main"
        aria-live="polite"
        className="mx-auto flex w-full max-w-[680px] flex-1 flex-col gap-4 px-5 py-5"
      >
        {/* context_token 만료 안내 (CLAUDE.md §9) - 대화 내용은 이미 초기화됨 */}
        {expired && (
          <div
            role="status"
            className="card-enter overflow-hidden rounded-card border border-border bg-white shadow-card"
          >
            <div className="border-b border-border-soft bg-card-head px-4 py-3.5">
              <span className="inline-flex rounded-[8px] border border-primary-border bg-primary-light px-2.5 py-1 text-caption font-extrabold text-primary">
                새 대화 안내
              </span>
            </div>
            <div className="flex flex-col gap-3.5 p-4">
              <p className="text-body-lg font-semibold text-text [text-wrap:pretty]">
                안전을 위해 대화가 종료되었습니다. 새 대화를 시작해 주세요.
              </p>
              <button
                type="button"
                onClick={startNewConversation}
                className="min-h-14 w-full rounded-btn bg-primary px-4 text-[18px] font-bold text-white hover:bg-primary-dark active:bg-primary-dark"
              >
                새 대화 시작
              </button>
              <p className="text-note text-text-sub">
                이전 대화 내용은 저장되지 않았습니다.
              </p>
            </div>
          </div>
        )}
        {!expired && messages.length === 0 && !loading && (
          <p className="py-8 text-center text-body text-text-sub">
            궁금한 민원을 입력해 주세요.
          </p>
        )}
        {messages.map((msg) =>
          msg.role === "user" ? (
            <div key={msg.id} className="flex justify-end">
              <p className="max-w-[85%] rounded-[16px_16px_4px_16px] bg-primary px-4 py-3 text-body leading-[1.45] text-white">
                {msg.text}
              </p>
            </div>
          ) : (
            <BotResponse key={msg.id} message={msg} ask={ask} />
          ),
        )}
        {loading && <LoadingSkeleton />}
        <div ref={bottomRef} />
      </main>

      {/* 하단 sticky 입력바 - 위에 개인정보 경고 한 줄 (§8) */}
      <div className="sticky bottom-0 border-t border-border-soft bg-white">
        <form
          onSubmit={submit}
          className="mx-auto w-full max-w-[680px] px-5 pt-1 pb-3"
        >
          {/* 개인정보 경고 한 줄 - 입력 위 (§8) */}
          <PrivacyNotice />
          <div className="mt-2 flex gap-2">
            <label htmlFor="chat-input" className="sr-only">
              질문 입력
            </label>
            <input
              id="chat-input"
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={
                expired ? "새 대화를 시작해 주세요" : "질문을 입력하세요"
              }
              disabled={expired}
              className="min-h-12 min-w-0 flex-1 rounded-btn border border-border bg-white px-4 text-body text-text placeholder:text-text-faint focus:border-primary disabled:bg-border-soft disabled:text-text-faint"
            />
            <button
              type="submit"
              disabled={loading || expired}
              className="min-h-12 shrink-0 rounded-btn bg-primary px-5 text-body font-bold text-white hover:bg-primary-dark active:bg-primary-dark disabled:bg-border-soft disabled:text-text-faint"
            >
              전송
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

/** 응답 타입별 카드 분기 */
function BotResponse({
  message,
  ask,
}: {
  message: BotMessage;
  ask: (
    question: string,
    opts?: { region?: string; displayText?: string },
  ) => Promise<void>;
}) {
  const { response, id, question } = message;

  switch (response.result_type) {
    case "SUCCESS":
      return (
        <AnswerCard
          response={response}
          responseId={id}
          onRegionChange={
            response.region
              ? (dong) =>
                  void ask(question, {
                    region: dong,
                    displayText: `${dong} 기준으로 다시 알려주세요`,
                  })
              : undefined
          }
          onAskRelated={(q) => void ask(q)}
        />
      );
    case "FOLLOWUP":
      return (
        <FollowupCard
          response={response}
          responseId={id}
          onSelectQuestion={(q) => void ask(q)}
          onSelectRegion={(dong, regionQuestion) =>
            void ask(regionQuestion, {
              region: dong,
              displayText: `${dong}에 살아요`,
            })
          }
        />
      );
    case "FALLBACK":
      return <FallbackCard response={response} responseId={id} />;
    case "ERROR":
      // 네트워크 오류 - 재시도가 주인공, 뱃지만 danger 톤 (§6-4)
      return (
        <div
          role="alert"
          className="card-enter overflow-hidden rounded-card border border-border bg-white shadow-card"
        >
          <div className="border-b border-border-soft bg-card-head px-4 py-3.5">
            <span className="inline-flex rounded-[8px] bg-danger-light px-2.5 py-1 text-caption font-extrabold text-danger">
              연결 오류
            </span>
          </div>
          <div className="flex flex-col gap-3.5 p-4">
            <p className="text-body-lg font-semibold text-text [text-wrap:pretty]">
              연결이 잠시 끊겼어요.{" "}
              <b className="font-bold">작성하신 질문은 그대로 남아 있습니다.</b>
            </p>
            <button
              type="button"
              onClick={() => void ask(question, { region: message.region })}
              className="min-h-14 w-full rounded-btn bg-primary px-4 text-[18px] font-bold text-white hover:bg-primary-dark active:bg-primary-dark"
            >
              다시 시도
            </button>
            <a
              href="tel:044-120"
              className="flex min-h-14 w-full items-center justify-center rounded-btn border border-primary bg-white px-4 text-[18px] font-bold text-primary hover:bg-hover-tint active:bg-hover-tint"
            >
              전화로 문의 044-120
            </a>
            <p className="text-note text-text-sub">
              잠시 후에도 연결되지 않으면 통신 상태를 확인해 주세요.
            </p>
          </div>
        </div>
      );
  }
}

export default function ChatPage() {
  return (
    <Suspense fallback={<LoadingSkeleton />}>
      <ChatScreen />
    </Suspense>
  );
}
