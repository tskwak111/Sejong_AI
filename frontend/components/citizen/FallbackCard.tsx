"use client";

/**
 * (C) FALLBACK 카드 4종 - DESIGN.md v3 §6-3 (시안 2b).
 * 오류가 아닌 "다음 행동" 문법 - danger(빨강) 절대 금지 (§2).
 * 공통 구조: 헤더 뱃지(primary-light 문법) → 리드 문장 → CTA1(primary 채움
 * 56px) → CTA2(outline, 필요시) → 하단 노트(기관 정보 + 안심 문구).
 * 출처 블록·도장 없음 - 의도된 부재 (검증된 답변이 아니므로).
 * PERSONAL_LOOKUP은 공식 조회 채널 딥링크가 CTA1 (예: 위택스).
 */
import type { FallbackCode, FallbackResponse } from "@/types/api";
import { CATEGORY_LABEL } from "@/types/api";
import FeedbackButtons from "@/components/citizen/FeedbackButtons";

/** 헤더 뱃지 라벨 (§6-3 표) */
const FALLBACK_BADGE: Record<FallbackCode, string> = {
  INSUFFICIENT_GROUNDING: "확인 후 안내",
  PERSONAL_LOOKUP: "담당 부서 연결",
  LEGAL_JUDGMENT: "전문 상담 연결",
  OUT_OF_SCOPE: "다른 창구 안내",
};

const ctaFill =
  "flex min-h-14 w-full items-center justify-center rounded-btn bg-primary px-4 text-[18px] font-bold text-white hover:bg-primary-dark active:bg-primary-dark";
const ctaOutline =
  "flex min-h-14 w-full items-center justify-center rounded-btn border border-primary bg-white px-4 text-[18px] font-bold text-primary hover:bg-hover-tint active:bg-hover-tint";

export default function FallbackCard({
  response,
  responseId,
}: {
  response: FallbackResponse;
  responseId: string;
}) {
  const { fallback_code: code, contact, deep_link } = response;
  const phoneNumber = contact.phone.split(" ")[0];
  /** 전화 CTA 라벨용 축약 기관명 - "세종특별자치시 세정과" → "세정과" */
  const shortName = contact.name.split(" ").at(-1) ?? contact.name;
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
  const deepLinkCta = deep_link && (
    <a
      href={deep_link.url}
      target="_blank"
      rel="noopener noreferrer"
      className={`${ctaFill} gap-1.5`}
    >
      {deep_link.label}
      {externalIcon}
    </a>
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
        {/* 리드 문장 - 사유 안내 */}
        <p className="text-body-lg font-semibold text-text [text-wrap:pretty]">
          {response.message}
        </p>

        {/* OUT_OF_SCOPE: 지원 4개 분야 칩 재안내 */}
        {code === "OUT_OF_SCOPE" && (
          <ul className="flex flex-wrap gap-2">
            {Object.values(CATEGORY_LABEL).map((label) => (
              <li
                key={label}
                className="rounded-btn-s border border-primary-border bg-primary-light px-3 py-2 text-note font-bold text-primary"
              >
                {label}
              </li>
            ))}
          </ul>
        )}

        {/* CTA 구성 (§6-3 표) - PERSONAL_LOOKUP은 공식 조회 채널이 CTA1 */}
        {code === "PERSONAL_LOOKUP" ? (
          <>
            {deepLinkCta}
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
        ) : (
          // LEGAL_JUDGMENT / OUT_OF_SCOPE - 담당 부서·대표전화 연결
          telCta(ctaFill)
        )}

        {/* 하단 노트 - 기관 정보(이름·연락처·운영시간, DAR-002) + 안심 문구.
            §13-1: " · " 금지 - 줄바꿈으로 구분 */}
        <div className="text-note leading-[1.5] text-text-sub">
          <p className="font-semibold text-text">{contact.name}</p>
          <p>
            <a
              href={`tel:${phoneNumber}`}
              className="text-primary underline hover:text-primary-dark"
            >
              {contact.phone}
            </a>
          </p>
          <p>
            {contact.hours}에 상담원이 연결돼요.
            {code === "LEGAL_JUDGMENT" && " 방문 상담도 같은 시간에 가능해요."}
          </p>
          <p className="mt-1">질문 내용은 저장되지 않았습니다.</p>
        </div>
      </div>

      {/* 만족/불만족 - 폴백 불만족은 "과잉 폴백" 판정 데이터 (§6-5) */}
      <FeedbackButtons responseId={responseId} />
    </article>
  );
}
