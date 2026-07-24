"use client";

/**
 * 불만족 사유 시트 - DESIGN.md v3 §6-5 (하단 시트, --shadow-raised).
 * 분야 4개 + 사유 코드 선택형 라디오만. 자유 텍스트 입력란 없음 = 명시적 설계
 * (CLAUDE.md §9 - 질문 원문 미전송). 선택 칩 규칙 §11: 선택 = primary 채움 + ✓,
 * 미선택 형제 opacity 0.45.
 *
 * 계약(openapi-v1.yaml)에 피드백 엔드포인트가 없어 전송은 연결하지 않는다 -
 * 선택 결과는 탭 메모리에서만 소비된다 (계약 변경 필요 항목으로 보고됨).
 */
import { useState } from "react";
import {
  INTENT_LABEL,
  SUPPORTED_INTENTS,
  type SupportedIntent,
} from "@/lib/labels";

const REASON_CODES: { code: string; label: string }[] = [
  { code: "INACCURATE", label: "답변 내용이 정확하지 않아요" },
  { code: "NOT_RELEVANT", label: "질문과 관련 없는 답변이에요" },
  { code: "HARD_TO_UNDERSTAND", label: "안내가 이해하기 어려워요" },
  { code: "WRONG_CONTACT", label: "연결된 기관·링크가 잘못됐어요" },
];

/** 선택 칩 스타일 (§11) - 선택 = primary 채움 + ✓ / 미선택 형제 opacity 0.45 */
function chipClass(selected: boolean, anySelected: boolean) {
  if (selected) return "bg-primary font-bold text-white";
  return `border border-border bg-white text-text hover:border-primary hover:bg-hover-tint ${
    anySelected ? "opacity-45" : ""
  }`;
}

export default function FeedbackReasonSheet({
  open,
  onClose,
  onSubmit,
}: {
  open: boolean;
  onClose: () => void;
  /** 보내기 - 분야 + 사유 코드만 전달 (자유 텍스트 없음) */
  onSubmit: (category: SupportedIntent, reasonCode: string) => void;
}) {
  const [category, setCategory] = useState<SupportedIntent | null>(null);
  const [reason, setReason] = useState<string | null>(null);

  if (!open) return null;

  const canSubmit = category !== null && reason !== null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="불만족 사유 선택"
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-4 md:items-center"
    >
      <div className="sheet-enter w-full max-w-md rounded-card bg-white p-6 shadow-raised">
        <h2 className="text-card-title font-extrabold text-text">
          어떤 점이 아쉬웠나요?
        </h2>
        <p className="mt-1 text-note text-text-sub">
          해당하는 항목만 선택해 주세요. 질문 내용은 전송되지 않아요.
        </p>

        <fieldset className="mt-4">
          <legend className="text-note font-bold text-text">민원 분야</legend>
          <div className="mt-2 grid grid-cols-2 gap-2">
            {SUPPORTED_INTENTS.map((key) => (
              <label
                key={key}
                className={`flex min-h-11 cursor-pointer items-center gap-1.5 rounded-btn-s px-3 text-note ${chipClass(
                  category === key,
                  category !== null,
                )}`}
              >
                <input
                  type="radio"
                  name="feedback-category"
                  value={key}
                  checked={category === key}
                  onChange={() => setCategory(key)}
                  className="sr-only"
                />
                {category === key && (
                  <span aria-hidden="true" className="text-[13px]">
                    ✓
                  </span>
                )}
                {INTENT_LABEL[key]}
              </label>
            ))}
          </div>
        </fieldset>

        <fieldset className="mt-4">
          <legend className="text-note font-bold text-text">불만족 사유</legend>
          <div className="mt-2 flex flex-col gap-2">
            {REASON_CODES.map(({ code, label }) => (
              <label
                key={code}
                className={`flex min-h-11 cursor-pointer items-center gap-1.5 rounded-btn-s px-3 text-note ${chipClass(
                  reason === code,
                  reason !== null,
                )}`}
              >
                <input
                  type="radio"
                  name="feedback-reason"
                  value={code}
                  checked={reason === code}
                  onChange={() => setReason(code)}
                  className="sr-only"
                />
                {reason === code && (
                  <span aria-hidden="true" className="text-[13px]">
                    ✓
                  </span>
                )}
                {label}
              </label>
            ))}
          </div>
        </fieldset>

        <div className="mt-5 flex gap-2">
          <button
            type="button"
            onClick={onClose}
            className="min-h-11 flex-1 rounded-btn border border-border bg-white px-4 text-note font-semibold text-text hover:bg-bg-sub active:bg-bg-sub"
          >
            닫기
          </button>
          <button
            type="button"
            disabled={!canSubmit}
            onClick={() => {
              if (category && reason) onSubmit(category, reason);
            }}
            className="min-h-11 flex-1 rounded-btn bg-primary px-4 text-note font-bold text-white hover:bg-primary-dark active:bg-primary-dark disabled:bg-border-soft disabled:text-text-faint"
          >
            보내기
          </button>
        </div>
      </div>
    </div>
  );
}
