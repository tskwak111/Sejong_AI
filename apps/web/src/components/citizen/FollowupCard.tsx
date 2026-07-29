"use client";

/**
 * (B) FOLLOWUP 후속질문 카드 - DESIGN.md v3 §6-2 (시안 2a).
 * 단정적 답변을 절대 보여주지 않는다. 헤더 뱃지 "확인 질문" +
 * 리드 문장 + 선택지 버튼(56px, 1.5px primary-border).
 * 선택 직후: 카드가 요약형으로 전환 - 선택 칩 primary 채움 + ✓,
 * 미선택 형제 opacity 0.45. 그 아래 답변 카드가 이어진다.
 *
 * 계약의 followup_options는 문자열 배열이다. 지역명(3개동) 옵션은 지도 핀
 * 아이콘으로 표시하고, 선택 의미(질문 재전송 vs selected_region 승격)는
 * 부모(chat-screen)가 결정한다.
 */
import { useState } from "react";
import type { Intent } from "@/lib/chat-api";
import { isRegion } from "@/lib/labels";
import FeedbackButtons from "@/components/citizen/FeedbackButtons";
import type { FeedbackTransport } from "@/lib/feedback-api";

export default function FollowupCard({
  options,
  intent,
  disabled = false,
  onSelect,
  requestId,
  feedbackTransport,
}: {
  options: readonly string[];
  intent: Intent;
  disabled?: boolean;
  requestId: string;
  feedbackTransport?: FeedbackTransport;
  /** 선택지 클릭 - 부모가 지역 승격/질문 재전송을 결정 */
  onSelect: (option: string) => void;
}) {
  const [selected, setSelected] = useState<string | null>(null);
  const prompt = options.every(isRegion)
    ? "안내는 사시는 동에 따라 달라요. 어느 동에 거주하시나요?"
    : intent === "CERTIFICATE_ISSUANCE"
      ? "어떤 주민등록 증명서가 필요하신가요?"
      : "어떤 것부터 안내해 드릴까요?";

  /* ---- 선택 직후 요약형 (§6-2) ---- */
  if (selected !== null) {
    return (
      <div className="card-enter flex flex-col gap-2 rounded-card border border-border bg-white p-4 shadow-card">
        <p className="text-label font-bold text-text-sub">
          {prompt}
        </p>
        <ul className="flex flex-col gap-2">
          {options.map((opt) => (
            <li key={opt}>
              {opt === selected ? (
                <div className="flex min-h-14 w-full items-center justify-between gap-2 rounded-btn bg-primary px-4 py-2.5">
                  <span className="text-body font-bold text-white">{opt}</span>
                  <span
                    aria-hidden="true"
                    className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-white/25 text-[13px] font-extrabold text-white"
                  >
                    ✓
                  </span>
                </div>
              ) : (
                <div className="flex min-h-11 w-full items-center rounded-btn border-[1.5px] border-border-soft px-4 py-2 opacity-45">
                  <span className="text-[16px] font-semibold text-text-sub">
                    {opt}
                  </span>
                </div>
              )}
            </li>
          ))}
        </ul>
      </div>
    );
  }

  /* ---- 선택 전 ---- */
  return (
    <article className="card-enter overflow-hidden rounded-card border border-border bg-white shadow-card">
      {/* 헤더 뱃지 - SUCCESS 유형 뱃지와 동일 문법 */}
      <div className="border-b border-border-soft bg-card-head px-4 py-3.5">
        <span className="inline-flex rounded-[8px] border border-primary-border bg-primary-light px-2.5 py-1 text-caption font-extrabold text-primary">
          확인 질문
        </span>
      </div>

      <div className="flex flex-col gap-3.5 p-4">
        {/* 리드 문장 - FOLLOWUP의 summary는 계약상 null이라 UI가 소유한다 */}
        <p className="text-body-lg font-semibold text-text [text-wrap:pretty]">
          {prompt}
        </p>

        {/* 선택지 - 전체 폭, 56px, 1.5px primary-border */}
        <ul className="flex flex-col gap-2" aria-label="후속 질문 선택지">
          {options.map((opt) => (
            <li key={opt}>
              <button
                type="button"
                disabled={disabled}
                onClick={() => {
                  setSelected(opt);
                  onSelect(opt);
                }}
                className="flex min-h-14 w-full flex-col items-start gap-px rounded-btn border-[1.5px] border-primary-border bg-white px-4 py-2.5 text-left hover:border-primary hover:bg-hover-tint active:bg-hover-tint disabled:opacity-60"
              >
                <span className="flex items-center gap-1.5 text-body font-bold text-primary">
                  {isRegion(opt) && (
                    <svg
                      aria-hidden="true"
                      className="h-5 w-5 shrink-0"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth={1.8}
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 0 1 16 0Z" />
                      <circle cx="12" cy="10" r="3" />
                    </svg>
                  )}
                  {opt}
                </span>
              </button>
            </li>
          ))}
        </ul>

        {/* 하단 안내 */}
        <p className="text-note leading-[1.5] text-text-sub">
          골라도 되고, 질문을 다시 써도 돼요. 선택하시면{" "}
          <b className="font-bold text-text">공식 출처를 확인해</b> 답해드립니다.
        </p>
      </div>

      {/* 만족/불만족 - 모든 응답 공통 (§6-5) */}
      <FeedbackButtons requestId={requestId} transport={feedbackTransport} />
    </article>
  );
}
