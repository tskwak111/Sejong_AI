"use client";

/**
 * (C) FALLBACK 카드 - DESIGN.md v3 §6-3 (시안 2b), 계약 폴백 6종.
 * 오류가 아닌 "다음 행동" 문법 - danger(빨강) 절대 금지 (§2).
 * 공통 구조: 헤더 뱃지(primary-light 문법) → 제목(fallback.title) →
 * 리드 문장(fallback.message) → next_actions → CTA → 하단 노트(기관 정보).
 * 출처 블록·도장 없음 - 의도된 부재 (검증된 답변이 아니므로).
 *
 * 계약 적응:
 * - 사유 6종 (CIVIC_SCOPE_GAP·PRIVACY_UNRESOLVED 포함)
 * - 기관 정보는 fallback.office(Office|null) - 없으면 민원콜센터 상수
 * - PERSONAL_LOOKUP의 공식 조회 채널 딥링크는 계약에 없어 UI 상수 사용 (보고 항목)
 */
import type { components } from "../../../../../packages/shared-contracts/src/generated/api";
import {
  CALL_CENTER,
  INTENT_LABEL,
  PERSONAL_LOOKUP_DEEP_LINK,
  SUPPORTED_INTENTS,
  type FallbackReason,
} from "@/lib/labels";
import FeedbackButtons from "@/components/citizen/FeedbackButtons";
import type { FeedbackTransport } from "@/lib/feedback-api";

type Fallback = components["schemas"]["Fallback"];

/** 헤더 뱃지 라벨 (§6-3 표 + PRIVACY_UNRESOLVED) */
const FALLBACK_BADGE: Record<FallbackReason, string> = {
  INSUFFICIENT_GROUNDING: "확인 후 안내",
  PERSONAL_LOOKUP: "담당 부서 연결",
  LEGAL_JUDGMENT: "전문 상담 연결",
  CIVIC_SCOPE_GAP: "지원 확대 검토",
  OUT_OF_SCOPE: "다른 창구 안내",
  PRIVACY_UNRESOLVED: "다시 질문 안내",
};

const ctaFill =
  "flex min-h-14 w-full items-center justify-center rounded-btn bg-primary px-4 text-[18px] font-bold text-white hover:bg-primary-dark active:bg-primary-dark";
const ctaOutline =
  "flex min-h-14 w-full items-center justify-center rounded-btn border border-primary bg-white px-4 text-[18px] font-bold text-primary hover:bg-hover-tint active:bg-hover-tint";

export default function FallbackCard({
  fallback,
  requestId,
  feedbackTransport,
}: {
  fallback: Fallback;
  requestId: string;
  feedbackTransport?: FeedbackTransport;
}) {
  const code = fallback.reason;
  const office = fallback.office ?? null;
  const contactName = office?.office_name ?? CALL_CENTER.name;
  const contactPhone = office?.phone ?? CALL_CENTER.phone;
  const contactHours = office?.opening_hours ?? CALL_CENTER.hours;
  const phoneNumber = contactPhone.split(" ")[0];
  /** 전화 CTA 라벨용 축약 기관명 - "세종특별자치시 세정과" → "세정과" */
  const shortName = contactName.split(" ").at(-1) ?? contactName;
  const telLabel = `${shortName} 전화 ${phoneNumber}`;

  const telCta = (style: string) => (
    <a href={`tel:${phoneNumber}`} className={style}>
      {telLabel}
    </a>
  );
  /* 외부 링크 아이콘 (§14 체크리스트) */
  const externalIcon = (
    <svg
      aria-hidden="true"
      className="h-4 w-4"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M15 3h6v6" />
      <path d="M10 14 21 3" />
      <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
    </svg>
  );

  return (
    <article className="card-enter overflow-hidden rounded-card border border-border bg-white shadow-card">
      {/* 헤더 뱃지 - primary-light 문법 (danger 금지) */}
      <div className="border-b border-border-soft bg-card-head px-4 py-3.5">
        <span className="inline-flex rounded-[8px] border border-primary-border bg-primary-light px-2.5 py-1 text-caption font-extrabold text-primary">
          {FALLBACK_BADGE[code]}
        </span>
      </div>

      <div className="flex flex-col gap-3.5 p-4">
        {/* 제목 + 리드 문장 - 사유 안내 (계약 title/message) */}
        <div>
          <h2 className="text-card-title font-extrabold text-text [text-wrap:pretty]">
            {fallback.title}
          </h2>
          <p className="mt-1.5 text-body-lg font-semibold text-text [text-wrap:pretty]">
            {fallback.message}
          </p>
        </div>

        {/* 다음 행동 목록 (계약 next_actions) */}
        {fallback.next_actions && fallback.next_actions.length > 0 && (
          <ul className="flex flex-col gap-1.5">
            {fallback.next_actions.map((action) => (
              <li
                key={action}
                className="flex items-start gap-1.5 text-body text-text"
              >
                <svg
                  aria-hidden="true"
                  className="mt-1 h-4 w-4 shrink-0 text-primary"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={2.2}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M20 6 9 17l-5-5" />
                </svg>
                {action}
              </li>
            ))}
          </ul>
        )}

        {/* OUT_OF_SCOPE: 지원 4개 분야 칩 재안내 */}
        {code === "OUT_OF_SCOPE" && (
          <ul className="flex flex-wrap gap-2">
            {SUPPORTED_INTENTS.map((intent) => (
              <li
                key={intent}
                className="rounded-btn-s border border-primary-border bg-primary-light px-3 py-2 text-note font-bold text-primary"
              >
                {INTENT_LABEL[intent]}
              </li>
            ))}
          </ul>
        )}

        {/* CTA 구성 (§6-3 표) */}
        {code === "PERSONAL_LOOKUP" ? (
          <>
            {/* 공식 조회 채널이 CTA1 (예: 위택스) - UI 상수 */}
            <a
              href={PERSONAL_LOOKUP_DEEP_LINK.url}
              target="_blank"
              rel="noopener noreferrer"
              className={`${ctaFill} gap-1.5`}
            >
              {PERSONAL_LOOKUP_DEEP_LINK.label}
              {externalIcon}
            </a>
            {telCta(ctaOutline)}
          </>
        ) : code === "INSUFFICIENT_GROUNDING" ? (
          <>
            {telCta(ctaFill)}
            <a
              href="https://www.gov.kr"
              target="_blank"
              rel="noopener noreferrer"
              className={`${ctaOutline} gap-1.5`}
            >
              정부24에서 찾아보기
              {externalIcon}
            </a>
          </>
        ) : code === "PRIVACY_UNRESOLVED" ? null : (
          // LEGAL_JUDGMENT / CIVIC_SCOPE_GAP / OUT_OF_SCOPE - 대표전화 연결
          telCta(ctaFill)
        )}

        {/* 하단 노트 - 기관 정보(이름·연락처·운영시간, DAR-002) + 안심 문구.
            PRIVACY_UNRESOLVED는 office가 항상 null이라 다시 질문 안내만 남긴다.
            §13-1: " · " 금지 - 줄바꿈으로 구분 */}
        {code === "PRIVACY_UNRESOLVED" ? (
          <p className="text-note leading-[1.5] text-text-sub">
            질문 내용은 저장되지 않았습니다. 개인정보를 빼고 다시 질문해 주세요.
          </p>
        ) : (
          <div className="text-note leading-[1.5] text-text-sub">
            <p className="font-semibold text-text">{contactName}</p>
            <p>
              <a
                href={`tel:${phoneNumber}`}
                className="text-primary underline hover:text-primary-dark"
              >
                {contactPhone}
              </a>
            </p>
            <p>
              {contactHours}에 상담원이 연결돼요.
              {code === "LEGAL_JUDGMENT" && " 방문 상담도 같은 시간에 가능해요."}
            </p>
            {office?.address && <p>{office.address}</p>}
            {/* 저장 정책 문구 - Q-MVP-002/D-059 (개인정보 최소수집 강화):
                INSUFFICIENT_GROUNDING만 마스킹 후 30일 보관.
                CIVIC_SCOPE_GAP은 별도 범위확대 queue에 마스킹 후 30일 보관.
                PERSONAL_LOOKUP·LEGAL_JUDGMENT·OUT_OF_SCOPE는 완전 미저장. */}
            <p className="mt-1">
              {code === "INSUFFICIENT_GROUNDING"
                ? "이 질문은 안내 개선을 위해 개인정보를 가린 채 30일간만 보관돼요."
                : code === "CIVIC_SCOPE_GAP"
                  ? "이 질문은 지원 범위 검토를 위해 개인정보를 가린 채 30일간만 보관돼요."
                  : "질문 내용은 저장되지 않았습니다."}
            </p>
          </div>
        )}
      </div>

      {/* 만족/불만족 - 폴백 불만족은 "과잉 폴백" 판정 데이터 (§6-5) */}
      <FeedbackButtons requestId={requestId} transport={feedbackTransport} />
    </article>
  );
}
