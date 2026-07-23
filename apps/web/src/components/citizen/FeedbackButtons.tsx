"use client";

/**
 * 만족/불만족 - 모든 응답 공통 (§6-5 + 세션 3 후속 수정 2).
 * 문구·버튼은 전 응답 통일: "이 안내가 도움이 되었나요?" +
 * 만족/불만족(엄지 아이콘, outline, 우측 정렬).
 * variant는 배치만 다르다 - "footer"(기본): FOLLOWUP·FALLBACK 카드 푸터 행 /
 * "inline": SUCCESS 카드 하단 행.
 * 클릭 시: 두 버튼이 사라지고 "의견을 보내주셔서 감사합니다" 한 줄. 재클릭 불가.
 * 불만족 → FeedbackReasonSheet(분야+사유 코드만, 자유 텍스트 없음 §9).
 *
 * 계약에 피드백 엔드포인트가 없어(보고 항목) 전송은 하지 않는다 -
 * 선택 상태는 현재 탭 메모리에서만 유지된다.
 */
import { useState } from "react";
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
  variant = "footer",
}: {
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
      <div className={inline ? "" : "border-t border-border-soft px-4 py-3.5"}>
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
          onClick={() => setVoted("up")}
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
        onSubmit={() => {
          // 계약에 전송 엔드포인트가 없어 선택 결과는 보관하지 않는다 (§9)
          setSheetOpen(false);
          setVoted("down");
        }}
      />
    </div>
  );
}
