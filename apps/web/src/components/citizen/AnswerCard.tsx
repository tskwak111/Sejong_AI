"use client";

/**
 * (A) SUCCESS 답변 카드 - DESIGN.md v3 §6-1 + "대화 화면 개정" 반영.
 * 순서: 헤더(유형 뱃지 + 지역 칩) → 요약(파란 틴트 강조) → 신청 방법(번호 원 +
 * 이음선) → 정보 표(헤어라인 정의 표) → 딥링크 CTA → 만족/불만족 → 출처 스트립.
 *
 * 데이터는 계약 SuccessResponse가 기준이다:
 * - summary/procedure_steps/required_documents/processing_time/fee/department
 * - 담당 기관은 office(Office) - 연락처·운영시간 포함 (DAR-002)
 * - 지역 칩은 요청의 selected_region을 UI가 승계 (응답에 지역 에코 없음)
 * - 딥링크는 계약에 없어 intent별 UI 상수 사용 (lib/labels.ts, 보고 항목)
 *
 * ⚠️ 출처(sources)와 최종 확인일(last_verified_at)이 없으면 카드를 렌더링하지
 * 않고 오류 UI를 보여준다 (SER-003 환각 방지, 출처 표기율 100% 보증 장치).
 */
import { Fragment, useState } from "react";
import type { components } from "../../../../../packages/shared-contracts/src/generated/api";
import {
  CALL_CENTER,
  DEEP_LINK_BY_INTENT,
  INTENT_LABEL,
  type Region,
} from "@/lib/labels";
import SourceBadge from "@/components/citizen/SourceBadge";
import FeedbackButtons from "@/components/citizen/FeedbackButtons";
import RegionSelect from "@/components/citizen/RegionSelect";

type SuccessResponse = components["schemas"]["SuccessResponse"];
type Office = components["schemas"]["Office"];

/**
 * 핵심 기한·수치 강조 (대화 화면 개정 2) - 파란 틴트 배경
 * (--color-highlight-text) + semibold + primary-dark, 패딩 1px 4px, 반경 4px.
 */
const NUMERIC_PATTERN =
  /(\d[\d,]*(?:~\d[\d,]*)?\s?(?:만\s?원|원|일|주|개월|시간)(?:\s?(?:이내|이하|이상))?~?)/g;

function HighlightedSummary({ text }: { text: string }) {
  const parts = text.split(NUMERIC_PATTERN);
  return (
    <>
      {parts.map((part, i) => {
        if (i % 2 === 0) return part;
        const lead = /^\s*/.exec(part)?.[0] ?? "";
        const trail = /\s*$/.exec(part)?.[0] ?? "";
        return (
          <Fragment key={i}>
            {lead}
            <b className="rounded-[4px] bg-highlight-text px-[4px] py-[1px] font-semibold text-primary-dark">
              {part.trim()}
            </b>
            {trail}
          </Fragment>
        );
      })}
    </>
  );
}

/** 섹션 라벨 - 15px 800 text-sub (v3 불변) */
function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="text-label font-extrabold tracking-[0.03em] text-text-sub">
      {children}
    </h3>
  );
}

/** 번호 원 28px - primary 채움 흰 숫자 (v3 불변) */
function StepNumber({ n }: { n: number }) {
  return (
    <span
      aria-hidden="true"
      className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary text-label font-extrabold text-white"
    >
      {n}
    </span>
  );
}

/** 정보 표의 한 행 - 라벨 셀 고정 96px(모바일 84px), 헤어라인만으로 구조 */
function InfoRow({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-start gap-3 py-3">
      <dt className="w-[84px] shrink-0 pt-0.5 text-caption font-bold text-text-sub min-[431px]:w-24">
        {label}
      </dt>
      <dd className="min-w-0 flex-1 text-caption text-text">{children}</dd>
    </div>
  );
}

/** 수수료 값 - 슬래시 구분이 3개 이상이면 항목당 한 줄 세로 나열 (개정 3) */
function FeeValue({ fee }: { fee: string }) {
  const parts = fee.split("/").map((p) => p.trim());
  if (parts.length >= 3) {
    return (
      <ul>
        {parts.map((p) => (
          <li key={p}>{p}</li>
        ))}
      </ul>
    );
  }
  return <>{fee}</>;
}

/** 담당 기관 행 - 기관명/전화/운영시간/주소 각 한 줄 (§13-1, DAR-002) */
function OfficeContact({ office }: { office: Office }) {
  return (
    <>
      <p className="font-semibold">{office.office_name}</p>
      <p>
        <a
          href={`tel:${office.phone.split(" ")[0]}`}
          className="text-primary underline hover:text-primary-dark"
        >
          {office.phone}
        </a>
      </p>
      {office.opening_hours && <p>{office.opening_hours}</p>}
      <p>{office.address}</p>
      {office.map_url && (
        <p>
          <a
            href={office.map_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary underline hover:text-primary-dark"
          >
            공식 지도 보기
          </a>
        </p>
      )}
    </>
  );
}

export default function AnswerCard({
  response,
  region,
  onRegionChange,
}: {
  response: SuccessResponse;
  /** 이 답변을 만든 요청의 selected_region - 있으면 "동 변경" 인라인 노출 (SFR-004) */
  region?: Region | null;
  onRegionChange?: (dong: Region) => void;
}) {
  const [showRegionSelect, setShowRegionSelect] = useState(false);

  // 출처 또는 최종 확인일 누락 → 답변 카드 렌더링 금지 (SER-003)
  const hasValidSources =
    response.sources.length > 0 &&
    response.sources.every((s) => s.source_id && s.last_verified_at);
  if (!hasValidSources) {
    return (
      <div
        role="alert"
        className="card-enter overflow-hidden rounded-card border border-border bg-white shadow-card"
      >
        <div className="border-b border-border-soft bg-card-head px-4 py-3.5">
          <span className="inline-flex rounded-[8px] bg-danger-light px-2.5 py-1 text-caption font-extrabold text-danger">
            일시적인 오류
          </span>
        </div>
        <div className="flex flex-col gap-3 p-4">
          <p className="text-body-lg font-semibold text-text [text-wrap:pretty]">
            답변의 근거(출처)를 확인하지 못했어요. 정확하지 않은 안내를 드리지
            않기 위해 답변을 표시하지 않습니다.
          </p>
          <p className="text-note text-text-sub">
            {CALL_CENTER.name}
            <br />
            <a
              href={`tel:${CALL_CENTER.phone}`}
              className="text-primary underline hover:text-primary-dark"
            >
              {CALL_CENTER.phone}
            </a>{" "}
            ({CALL_CENTER.hours})
          </p>
        </div>
      </div>
    );
  }

  const steps = response.procedure_steps ?? [];
  const documents = response.required_documents ?? [];
  const deepLink = DEEP_LINK_BY_INTENT[response.intent];

  return (
    <article className="card-enter overflow-hidden rounded-card border border-border bg-white shadow-card">
      {/* 1. 카드 헤더 - 유형 뱃지 + 지역 칩(동 변경 진입점) */}
      <div className="flex flex-wrap items-center gap-2 border-b border-border-soft bg-card-head px-4 py-3.5">
        <span className="rounded-[8px] border border-primary-border bg-primary-light px-2.5 py-1 text-caption font-extrabold text-primary">
          {INTENT_LABEL[response.intent]}
        </span>
        {region && (
          <span className="flex items-center rounded-[8px] bg-bg-sub px-2.5 py-1 text-caption font-bold text-text-sub">
            {region} 기준
            {onRegionChange && (
              <button
                type="button"
                aria-expanded={showRegionSelect}
                onClick={() => setShowRegionSelect((v) => !v)}
                className="-my-2 ml-1.5 flex min-h-11 items-center px-1 font-bold text-primary underline hover:text-primary-dark"
              >
                동 변경
              </button>
            )}
          </span>
        )}
      </div>

      <div className="p-4">
        <div className="flex flex-col gap-[18px]">
          {/* 2. 요약 - 파란 틴트 강조 (개정 2) */}
          <p className="text-body-lg font-semibold text-text [text-wrap:pretty]">
            <HighlightedSummary text={response.summary ?? "확인된 민원 안내"} />
          </p>

          {/* 3. 신청 방법 - 번호 원 + 이음선 (v3 불변) */}
          {steps.length > 0 && (
            <section aria-label="신청 방법" className="flex flex-col gap-2">
              <SectionLabel>신청 방법</SectionLabel>
              <ol className="flex flex-col">
                {steps.map((step, i) => (
                  <li key={step} className="flex gap-3">
                    {i < steps.length - 1 ? (
                      <span className="flex flex-col items-center">
                        <StepNumber n={i + 1} />
                        <span
                          aria-hidden="true"
                          className="min-h-3.5 w-0 flex-1 border-l-2 border-dotted border-tie-line"
                        />
                      </span>
                    ) : (
                      <StepNumber n={i + 1} />
                    )}
                    <div className="pb-3.5 last:pb-0">
                      <p className="pt-0.5 text-body font-bold text-text">
                        {step}
                      </p>
                    </div>
                  </li>
                ))}
              </ol>
            </section>
          )}

          {/* 4. 정보 표 (개정 3) - 헤어라인 정의 표, 값이 없는 행은 미렌더링 */}
          <dl
            aria-label="민원 정보"
            className="divide-y divide-border border-y border-border"
          >
            {documents.length > 0 && (
              <InfoRow label="필요 서류">
                <ul>
                  {documents.map((doc) => (
                    <li key={doc}>{doc}</li>
                  ))}
                </ul>
              </InfoRow>
            )}
            {response.processing_time && (
              <InfoRow label="처리 기간">{response.processing_time}</InfoRow>
            )}
            {response.fee && (
              <InfoRow label="수수료">
                <FeeValue fee={response.fee} />
              </InfoRow>
            )}
            {response.department && !response.office && (
              <InfoRow label="담당 부서">{response.department}</InfoRow>
            )}
            {response.office && (
              <InfoRow label="담당 기관">
                <OfficeContact office={response.office} />
              </InfoRow>
            )}
          </dl>

          {/* "동 변경" 인라인 동 선택 (SFR-004 - 별도 온보딩 화면 없음) */}
          {onRegionChange && showRegionSelect && (
            <div className="rounded-cell bg-bg-sub p-3">
              <RegionSelect
                current={region}
                label="다른 동으로 변경"
                onSelect={(dong) => {
                  setShowRegionSelect(false);
                  if (dong !== region) onRegionChange(dong);
                }}
              />
            </div>
          )}
        </div>

        {/* ---- 카드 하단 (개정 4): CTA → 피드백, 행 간 16px ---- */}
        <div className="mt-[18px] space-y-4">
          {/* 5. 딥링크 CTA - 카드 내 유일한 primary 채움 버튼, 56px.
              계약 응답에 deep_link가 없어 intent별 공식 채널 상수 사용 */}
          <a
            href={deepLink.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex min-h-14 w-full items-center justify-center gap-1.5 rounded-btn bg-primary px-4 text-[18px] font-bold text-white hover:bg-primary-dark active:bg-primary-dark"
          >
            {deepLink.label}
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
          </a>

          {/* 6. 만족/불만족 - 엄지 아이콘 outline, 한 줄 우측 정렬 (개정 4) */}
          <FeedbackButtons variant="inline" />
        </div>
      </div>

      {/* 7. 출처 스트립 - 카드 하단 (개정 4) */}
      <SourceBadge sources={response.sources} />
    </article>
  );
}
