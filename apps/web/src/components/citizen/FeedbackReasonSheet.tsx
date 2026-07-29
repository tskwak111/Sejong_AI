"use client";

/**
 * 불만족 사유 시트 - DESIGN.md v3 §6-5 (하단 시트, --shadow-raised).
 * 분야 4개+기타, 사유 코드와 기타 상세(최대 300자)를 지원한다. 상세는 서버에서
 * 개인정보 마스킹 후 30일만 보관하며 질문·답변 원문은 전송하지 않는다.
 * 선택 칩 규칙 §11: 선택 = primary 채움 + ✓,
 * 미선택 형제 opacity 0.45.
 *
 * 선택 결과는 FeedbackButtons가 actual/fixture transport에 전달한다. actual 모드는
 * 공개 피드백 API로 저장하고 fixture 모드는 네트워크 없이 시연한다.
 */
import { useEffect, useRef, useState } from "react";
import {
  INTENT_LABEL,
  SUPPORTED_INTENTS,
} from "@/lib/labels";
import type {
  FeedbackCategory,
  FeedbackReasonCode,
} from "@/lib/feedback-api";

const CATEGORY_OPTIONS: ReadonlyArray<{
  code: FeedbackCategory;
  label: string;
}> = [
  ...SUPPORTED_INTENTS.map((code) => ({ code, label: INTENT_LABEL[code] })),
  { code: "OTHER", label: "기타 민원" },
];

const REASON_CODES: {
  code: FeedbackReasonCode;
  label: string;
}[] = [
  { code: "INACCURATE", label: "답변 내용이 정확하지 않아요" },
  { code: "NOT_RELEVANT", label: "질문과 관련 없는 답변이에요" },
  { code: "HARD_TO_UNDERSTAND", label: "안내가 이해하기 어려워요" },
  { code: "WRONG_CONTACT", label: "연결된 기관·링크가 잘못됐어요" },
  { code: "OTHER", label: "기타 사유" },
];

const FOCUSABLE_SELECTOR = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  '[tabindex]:not([tabindex="-1"])',
].join(",");

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
  onSubmit: (
    category: FeedbackCategory,
    reasonCode: FeedbackReasonCode,
    detail: string | null,
  ) => void;
}) {
  const [category, setCategory] = useState<FeedbackCategory | null>(null);
  const [reason, setReason] = useState<FeedbackReasonCode | null>(null);
  const [detail, setDetail] = useState("");
  const dialogRef = useRef<HTMLDivElement>(null);
  const openerRef = useRef<HTMLElement | null>(null);
  const onCloseRef = useRef(onClose);

  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  useEffect(() => {
    if (!open) return;

    const dialog = dialogRef.current;
    if (!dialog) return;
    openerRef.current =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;

    const focusableElements = () => {
      const controls = Array.from(
        dialog.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR),
      );
      return controls.filter((control) => {
        if (
          !(control instanceof HTMLInputElement) ||
          control.type !== "radio" ||
          !control.name
        ) {
          return true;
        }
        const group = controls.filter(
          (candidate): candidate is HTMLInputElement =>
            candidate instanceof HTMLInputElement &&
            candidate.type === "radio" &&
            candidate.name === control.name,
        );
        return control === (group.find((candidate) => candidate.checked) ?? group[0]);
      });
    };

    focusableElements()[0]?.focus();

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onCloseRef.current();
        return;
      }
      if (event.key !== "Tab") return;

      const controls = focusableElements();
      if (controls.length === 0) return;
      const first = controls[0];
      const last = controls.at(-1)!;
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      openerRef.current?.focus();
      openerRef.current = null;
    };
  }, [open]);

  if (!open) return null;

  const canSubmit =
    category !== null &&
    reason !== null &&
    (reason !== "OTHER" || detail.trim().length > 0);

  return (
    <div
      ref={dialogRef}
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
          질문·답변 원문은 전송되지 않아요. 직접 입력 내용은 개인정보를
          가린 뒤 30일만 보관합니다.
        </p>

        <fieldset className="mt-4">
          <legend className="text-note font-bold text-text">민원 분야</legend>
          <div className="mt-2 grid grid-cols-2 gap-2">
            {CATEGORY_OPTIONS.map(({ code, label }) => (
              <label
                key={code}
                className={`flex min-h-11 cursor-pointer items-center gap-1.5 rounded-btn-s px-3 text-note focus-within:outline focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-primary ${chipClass(
                  category === code,
                  category !== null,
                )}`}
              >
                <input
                  type="radio"
                  name="feedback-category"
                  value={code}
                  checked={category === code}
                  onChange={() => setCategory(code)}
                  className="sr-only"
                />
                {category === code && (
                  <span aria-hidden="true" className="text-[13px]">
                    ✓
                  </span>
                )}
                {label}
              </label>
            ))}
          </div>
        </fieldset>

        {reason === "OTHER" && (
          <div className="mt-4">
            <label
              htmlFor="feedback-detail"
              className="text-note font-bold text-text"
            >
              불만족 상세 내용
            </label>
            <textarea
              id="feedback-detail"
              value={detail}
              maxLength={300}
              rows={3}
              onChange={(event) => setDetail(event.target.value)}
              className="mt-2 w-full resize-y rounded-btn-s border border-border px-3 py-2 text-note text-text focus:border-primary focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-primary"
              placeholder="개인정보는 적지 말아 주세요."
            />
            <p className="mt-1 text-right text-caption text-text-faint">
              {detail.length}/300
            </p>
          </div>
        )}

        <fieldset className="mt-4">
          <legend className="text-note font-bold text-text">불만족 사유</legend>
          <div className="mt-2 flex flex-col gap-2">
            {REASON_CODES.map(({ code, label }) => (
              <label
                key={code}
                className={`flex min-h-11 cursor-pointer items-center gap-1.5 rounded-btn-s px-3 text-note focus-within:outline focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-primary ${chipClass(
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
              if (category && reason && canSubmit) {
                onSubmit(
                  category,
                  reason,
                  reason === "OTHER" ? detail.trim() : null,
                );
              }
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
