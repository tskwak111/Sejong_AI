"use client";

/**
 * (A) SUCCESS 답변 카드 - DESIGN.md v3 §6-1 + "대화 화면 개정" + 세션 3 후속
 * 수정 1(출처 표시는 하단 스트립 하나로 통일 - 상단 뱃지 없음).
 * 순서: 헤더(유형 뱃지 + 지역 칩) → 요약(파란 틴트 강조, 개정 2) →
 * 신청 방법(2갈래 + 이음선, 불변) → 정보 표(헤어라인 정의 표, 개정 3) →
 * 주의사항(앰버 아이콘 + 회색 배경, 개정 3) → 딥링크 CTA → 만족/불만족
 * (엄지 아이콘 inline, 개정 4) → 함께 확인 칩 → 출처 스트립 (개정 4).
 *
 * ⚠️ 출처(sources)와 최종 확인일(last_verified_at)이 없으면 카드를 렌더링하지
 * 않고 오류 UI를 보여준다 (SER-003 환각 방지, 출처 표기율 100% 보증 장치).
 */
import { Fragment, useState } from "react";
import type { SuccessResponse } from "@/types/api";
import { CATEGORY_LABEL } from "@/types/api";
import SourceBadge from "@/components/citizen/SourceBadge";
import FeedbackButtons from "@/components/citizen/FeedbackButtons";
import RegionSelect from "@/components/citizen/RegionSelect";

/**
 * 핵심 기한·수치 강조 (대화 화면 개정 2) - 파란 틴트 배경
 * (--color-highlight-text) + semibold + primary-dark, 패딩 1px 4px, 반경 4px.
 * 노란 --color-highlight는 본문 강조에 사용 금지 (이음센터 행 펄스 전용).
 * 표시 계층 정규식 처리, mock 데이터 불변.
 */
const NUMERIC_PATTERN =
  /(\d[\d,]*(?:~\d[\d,]*)?\s?(?:만\s?원|원|일|주|개월|시간)(?:\s?(?:이내|이하|이상))?~?)/g;

function HighlightedSummary({ text }: { text: string }) {
  const parts = text.split(NUMERIC_PATTERN);
  return (
    <>
      {parts.map((part, i) => {
        if (i % 2 === 0) return part;
        // 최종 폴리시 5: 강조 배경은 원문에 밀착 - 양끝 공백은 하이라이트 밖에,
        // 패딩 1px 4px만. (괄호는 패턴상 캡처되지 않아 항상 밖에 남는다)
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

/**
 * 정보 표의 한 행 (대화 화면 개정 3) - 라벨 셀 고정 96px(모바일 84px),
 * 14px text-sub 상단 정렬 + 값 셀 14px text(라벨과 동일 크기로 수정).
 * 헤어라인만으로 구조, 배경·모서리 없음. 라벨은 현행 볼드 웨이트 유지.
 */
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

export default function AnswerCard({
  response,
  responseId,
  onRegionChange,
  onAskRelated,
}: {
  response: SuccessResponse;
  responseId: string;
  /** 답변에 지역 조건이 있을 때 "동 변경" 인라인 선택 콜백 (SFR-004) */
  onRegionChange?: (dong: string) => void;
  /** 관련 민원 제안 칩 탭 → 해당 질문 전송 (개정 4) */
  onAskRelated?: (question: string) => void;
}) {
  const [showRegionSelect, setShowRegionSelect] = useState(false);

  // 출처 또는 최종 확인일 누락 → 답변 카드 렌더링 금지 (SER-003)
  const hasValidSources =
    response.sources?.length > 0 &&
    response.sources.every((s) => s.kb_id && s.last_verified_at);
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
            {response.fallback_contact?.name}
            <br />
            <a
              href={`tel:${response.fallback_contact?.phone.split(" ")[0]}`}
              className="text-primary underline hover:text-primary-dark"
            >
              {response.fallback_contact?.phone}
            </a>{" "}
            ({response.fallback_contact?.hours})
          </p>
        </div>
      </div>
    );
  }

  // 신청 방법 - 2갈래(application_methods)가 없으면 절차형 단계로 같은 문법 (v3 불변)
  const methods =
    response.application_methods && response.application_methods.length > 0
      ? response.application_methods.map((m) => ({
          title: m.title,
          description: m.description,
        }))
      : response.procedure_steps.map((step) => ({
          title: step,
          description: undefined as string | undefined,
        }));

  return (
    <article className="card-enter overflow-hidden rounded-card border border-border bg-white shadow-card">
      {/* 1. 카드 헤더 - 유형 뱃지 + 지역 칩(동 변경 진입점).
          "공식 출처 확인됨" 상단 뱃지는 제거 - 출처 표시는 하단 스트립 하나로
          통일 (세션 3 후속 수정 1: 중복 해소, verify 문법은 스트립이 승계) */}
      <div className="flex flex-wrap items-center gap-2 border-b border-border-soft bg-card-head px-4 py-3.5">
        <span className="rounded-[8px] border border-primary-border bg-primary-light px-2.5 py-1 text-caption font-extrabold text-primary">
          {CATEGORY_LABEL[response.category]}
        </span>
        {response.region && (
          <span className="flex items-center rounded-[8px] bg-bg-sub px-2.5 py-1 text-caption font-bold text-text-sub">
            {response.region} 기준
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
            <HighlightedSummary text={response.answer_summary} />
          </p>

          {/* 3. 신청 방법 - 번호 원 + 이음선 (v3 불변) */}
          <section aria-label="신청 방법" className="flex flex-col gap-2">
            <SectionLabel>신청 방법</SectionLabel>
            <ol className="flex flex-col">
              {methods.map((m, i) => (
                <li key={i} className="flex gap-3">
                  {i < methods.length - 1 ? (
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
                      {m.title}
                    </p>
                    {m.description && (
                      <p className="text-[15.5px] leading-[1.45] text-text-sub">
                        {m.description}
                      </p>
                    )}
                  </div>
                </li>
              ))}
            </ol>
          </section>

          {/* 4. 정보 표 (개정 3) - 헤어라인 정의 표, 값이 없는 행은 미렌더링 */}
          <dl
            aria-label="민원 정보"
            className="divide-y divide-border border-y border-border"
          >
            {response.required_documents.length > 0 && (
              <InfoRow label="필요 서류">
                {/* 항목당 한 줄 세로 나열 (보조 설명은 괄호째 같은 항목) */}
                <ul>
                  {response.required_documents.map((doc) => (
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
            {response.fallback_contact && (
              <InfoRow label="담당 기관">
                {/* 기관명 한 줄 + 전화 한 줄 + 운영시간 한 줄 (점 구분자 없이 줄바꿈) */}
                <p className="font-semibold">{response.fallback_contact.name}</p>
                <p>
                  <a
                    href={`tel:${response.fallback_contact.phone.split(" ")[0]}`}
                    className="text-primary underline hover:text-primary-dark"
                  >
                    {response.fallback_contact.phone}
                  </a>
                </p>
                <p>{response.fallback_contact.hours}</p>
              </InfoRow>
            )}
          </dl>

          {/* "동 변경" 인라인 동 선택 (SFR-004 - 별도 온보딩 화면 없음) */}
          {onRegionChange && showRegionSelect && (
            <div className="rounded-cell bg-bg-sub p-3">
              <RegionSelect
                current={response.region}
                label="다른 동으로 변경"
                onSelect={(dong) => {
                  setShowRegionSelect(false);
                  if (dong !== response.region) onRegionChange(dong);
                }}
              />
            </div>
          )}

          {/* 5. 주의사항 - 표 아래, 카드당 유일한 강조 박스.
              앰버 아이콘 + 회색 배경 (개정 3) */}
          {response.caution && (
            <div className="rounded-btn bg-bg-sub px-3.5 py-3">
              <h3 className="flex items-center gap-1.5 text-note font-extrabold text-warning">
                <svg
                  aria-hidden="true"
                  className="h-4 w-4 shrink-0"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={2}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z" />
                  <path d="M12 9v4M12 17h.01" />
                </svg>
                주의사항
              </h3>
              <p className="mt-1 text-body text-text">{response.caution}</p>
            </div>
          )}
        </div>

        {/* ---- 카드 하단 (개정 4): CTA → 피드백 → 관련 칩, 행 간 16px ---- */}
        <div className="mt-[18px] space-y-4">
          {/* 6. 딥링크 CTA - 카드 내 유일한 primary 채움 버튼, 56px */}
          {response.deep_link && (
            <a
              href={response.deep_link.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex min-h-14 w-full items-center justify-center gap-1.5 rounded-btn bg-primary px-4 text-[18px] font-bold text-white hover:bg-primary-dark active:bg-primary-dark"
            >
              {response.deep_link.label}
              {/* 외부 링크 아이콘 (§14 체크리스트) */}
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
          )}

          {/* 7. 만족/불만족 - 엄지 아이콘 outline, 한 줄 우측 정렬 (개정 4) */}
          <FeedbackButtons responseId={responseId} variant="inline" />

          {/* 8. 함께 확인해 보세요 + 관련 질문 칩 (전체 폭 outline) */}
          {response.related_question && onAskRelated && (
            <div>
              <p className="text-caption font-bold text-text-sub">
                함께 확인해 보세요
              </p>
              {/* 최종 폴리시 7: 우측 화살표로 누르는 버튼임을 표시,
                  hover 시 primary-tint 배경 */}
              <button
                type="button"
                onClick={() => onAskRelated(response.related_question!)}
                className="mt-1 flex min-h-11 w-full items-center justify-between gap-2 rounded-btn-s border border-border bg-white px-3 py-2 text-left text-note text-text hover:border-primary hover:bg-primary-light hover:text-primary active:bg-primary-light"
              >
                {response.related_question}
                <svg
                  aria-hidden="true"
                  className="h-4 w-4 shrink-0"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={2}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M5 12h14" />
                  <path d="m13 6 6 6-6 6" />
                </svg>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* 9. 출처 스트립 - 카드 하단 (개정 4) */}
      <SourceBadge sources={response.sources} />
    </article>
  );
}
