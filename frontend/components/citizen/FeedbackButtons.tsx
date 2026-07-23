"use client";

/**
 * 만족/불만족 - 모든 응답 공통 (§6-5 + 세션 3 후속 수정 2).
 * 문구·버튼은 전 응답 통일: "이 안내가 도움이 되었나요?" +
 * 만족/불만족(엄지 아이콘, outline, 우측 정렬).
 * variant는 배치만 다르다 - "footer"(기본): FOLLOWUP·FALLBACK 카드 푸터 행
 * (상단 구분선 + 카드 패딩) / "inline": SUCCESS 카드 하단 행.
 * hover: 만족·불만족 동일한 연회색 테두리 - 초록/파랑 hover 금지
 * (색 역할 규칙: 초록은 검증 전용).
 * 클릭 시: 두 버튼이 사라지고 그 자리에 "의견을 보내주셔서 감사합니다"
 * 한 줄(15px, text-sub). 재클릭 불가.
 * 불만족 → FeedbackReasonSheet(분야+사유 코드만, 자유 텍스트 없음 §9)를
 * 거친 뒤 동일 문구로 전환. 시트를 닫으면 버튼 상태 유지.
 */
import { useState } from "react";
import { sendFeedback } from "@/lib/api";
import type { CivilCategory } from "@/types/api";
import FeedbackReasonSheet from "@/components/citizen/FeedbackReasonSheet";

function ThumbIcon({ down = false }: { down?: boolean }) {
  return (
    <svg
      aria-hidden="true"
      className={`h-4 w-4 ${down ? "rotate-180" : ""}`}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M7 10v12" />
      <path d="M15 5.9 14 10h5.5a2 2 0 0 1 1.9 2.6l-2.2 7A2 2 0 0 1 17.3 21H7V10l4-8a3 3 0 0 1 4 2.9Z" />
    </svg>
  );
}

export default function FeedbackButtons({
  responseId,
  variant = "footer",
}: {
  responseId: string;
  variant?: "footer" | "inline";
}) {
  const [voted, setVoted] = useState<"up" | "down" | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);

  const done = voted !== null;
  const inline = variant === "inline";

  /* hover 테두리: 만족·불만족 동일 - border보다 한 단계 진한 회색(text-faint).
     초록/파랑 hover 금지 (세션 3 후속 수정 2) */
  const btn =
    "flex min-h-[46px] items-center gap-1.5 rounded-btn-s border border-border bg-white font-bold text-text hover:border-text-faint active:bg-bg-sub";

  // 클릭 후: 두 버튼이 사라지고 그 자리에 감사 문구 한 줄 - 재클릭 불가
  if (done) {
    return (
      <div
        className={
          inline ? "" : "border-t border-border-soft px-4 py-3.5"
        }
      >
        <p role="status" className="py-2.5 text-note text-text-sub">
          의견을 보내주셔서 감사합니다
        </p>
      </div>
    );
  }

  return (
    <div
      className={`flex flex-wrap items-center justify-between gap-2.5 ${
        inline ? "" : "border-t border-border-soft px-4 py-3.5"
      }`}
    >
      <span className="text-[16px] font-semibold text-text-sub">
        이 안내가 도움이 되었나요?
      </span>

      <span className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => {
            setVoted("up");
            void sendFeedback({ response_id: responseId, satisfied: true });
          }}
          className={`${btn} px-4 text-[16px]`}
        >
          <ThumbIcon />
          만족
        </button>
        <button
          type="button"
          onClick={() => setSheetOpen(true)}
          className={`${btn} px-3.5 text-[16px]`}
        >
          <ThumbIcon down />
          불만족
        </button>
      </span>

      <FeedbackReasonSheet
        open={sheetOpen}
        onClose={() => setSheetOpen(false)}
        onSubmit={(category: CivilCategory, reasonCode: string) => {
          void sendFeedback({
            response_id: responseId,
            satisfied: false,
            category,
            reason_code: reasonCode,
          });
          setSheetOpen(false);
          setVoted("down");
        }}
      />
    </div>
  );
}
