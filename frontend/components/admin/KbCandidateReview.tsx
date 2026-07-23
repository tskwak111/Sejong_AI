"use client";

/**
 * KB 후보 상세 카드 - DESIGN.md v3 §9-3 (데모 #5의 클라이맥스).
 * 세로 3분할: 헤더(KB ID + 뱃지 + "AI 초안 생성" 시각) / 본문(발단 실패 질문
 * 요약 바 → AI 초안 정의 표 → 승인 전 확인 체크리스트) / 판정 바.
 * - 초안 필드 라벨은 한국어가 주 + 원 스키마명 12px 모노 병기 (§13-2).
 * - 출처 URL 행 = 검증 상태 표시 - 미검증이면 앰버 경고 (초안이 미완성으로
 *   보이는 것이 "사람이 판정한다"의 물증).
 * - 승인 버튼은 verify 초록 채움 - 이 화면 유일한 초록 채움 버튼 (§2).
 * - 승인 직후: 완료형 전환 + 우상단 승인 스탬프(2px dashed verify, -8deg,
 *   scale 1.6→1.0 200ms - §7-2 ③형, 날짜 + 승인자 실명).
 * - 반려는 사유 코드 선택만 (자유 텍스트 없음). 빨강은 반려 확정에만.
 */
import { useState } from "react";
import type {
  FailureQueueItem,
  KbCandidate,
  KbRejectReason,
} from "@/types/api";
import { CATEGORY_LABEL, FALLBACK_CODE_LABEL } from "@/types/api";

const REJECT_REASONS: { code: KbRejectReason; label: string }[] = [
  { code: "UNCLEAR_SOURCE", label: "출처 불명확" },
  { code: "INACCURATE", label: "내용 부정확" },
  { code: "DUPLICATE", label: "중복" },
  { code: "OTHER", label: "기타" },
];

/** §9-3 승인 전 확인 체크리스트 3항목 */
const CHECKLIST = [
  "출처 URL 접속 확인",
  "원문 대조",
  "연락처·운영시간 확인",
];

function formatDateTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function formatDate(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

/**
 * AI 초안 정의 표의 한 행 - 768px 이상: 라벨 셀 180px(admin-soft 배경) +
 * 값 셀 15.5px 좌우 2열. 768px 미만: 라벨(13px sub, 스키마명 병기) 위 +
 * 값(16px) 아래 상하 스택, 행 사이 헤어라인 유지 (모바일 정비 5).
 * 라벨은 한국어가 주 + 원 스키마명 모노 병기(백엔드 대조용, §13-2).
 */
function DraftRow({
  label,
  schema,
  children,
}: {
  label: string;
  schema: string;
  children: React.ReactNode;
}) {
  return (
    <div className="grid grid-cols-1 border-b border-border-soft last:border-b-0 md:grid-cols-[180px_1fr]">
      <dt className="px-4 pt-3 md:bg-admin-soft md:py-3">
        <span className="text-[13px] font-bold text-text-sub md:block md:text-caption">
          {label}
        </span>{" "}
        <span className="font-mono text-[12px] leading-[1.6] text-text-faint md:block">
          {schema}
        </span>
      </dt>
      <dd className="min-w-0 px-4 pt-1.5 pb-3 text-[16px] text-text md:py-3 md:text-admin-body">
        {children}
      </dd>
    </div>
  );
}

export default function KbCandidateReview({
  candidate,
  sourceFailure,
  busy,
  justApproved,
  approverName,
  onReview,
  onNext,
}: {
  candidate: KbCandidate;
  /** 발단이 된 실패 질문 - source_failure_id로 조회한 원본 (없으면 이력 미표시) */
  sourceFailure?: FailureQueueItem;
  busy: boolean;
  /** 승인 직후 완료형 전환 + 스탬프 연출 (§9-3) */
  justApproved: boolean;
  /** 승인 스탬프에 찍히는 승인자 표기 (최종 폴리시 10: 가상 실명 대신 직함) */
  approverName: string;
  onReview: (
    id: string,
    status: "승인" | "반려",
    reasonCode?: KbRejectReason,
  ) => void;
  /** 완료형의 "다음 후보 보기 →" */
  onNext: () => void;
}) {
  const [rejecting, setRejecting] = useState(false);
  const [rejectReason, setRejectReason] = useState<KbRejectReason | null>(null);
  const [checked, setChecked] = useState<Set<number>>(new Set());
  const { draft } = candidate;

  /* ── 승인 직후 완료형 (§9-3) ── */
  if (justApproved) {
    return (
      <article className="relative rounded-panel border border-border bg-white p-6">
        {/* 승인 스탬프 - §7-2 ③형, 승인 직후에만. 화면 내 유일한 도장 */}
        <div
          aria-hidden="true"
          className="stamp-enter absolute top-4 right-5 flex w-[104px] rotate-[-8deg] flex-col items-center gap-px rounded-btn border-2 border-dashed border-verify bg-verify-light/90 py-1.5"
        >
          <span className="text-[17px] font-extrabold tracking-[0.14em] text-verify-dark">
            승 인
          </span>
          <span className="text-[11px] font-bold text-verify-dark tabular-nums">
            {formatDate(new Date())}
          </span>
          <span className="text-[11px] font-bold text-verify-dark">
            {approverName}
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-2.5 pr-[130px]">
          <span className="font-mono text-[13px] font-extrabold text-primary">
            {candidate.id.toUpperCase()}
          </span>
          <span className="rounded-chip bg-verify-light-2 px-2 py-[3px] text-[12.5px] font-extrabold text-verify-dark">
            ACTIVE
          </span>
        </div>
        <h2 className="mt-2 pr-[130px] text-card-title font-extrabold text-text">
          {candidate.title}
        </h2>
        <div className="mt-2.5 flex flex-wrap items-center gap-x-3.5 gap-y-1">
          <p className="text-caption text-text-sub">
            다음 시민 답변부터 사용됩니다.
          </p>
          <button
            type="button"
            onClick={onNext}
            className="flex min-h-11 items-center text-caption font-bold text-primary underline hover:text-primary-dark"
          >
            다음 후보 보기 →
          </button>
        </div>
      </article>
    );
  }

  /* ── 승인 대기 상세 ── */
  return (
    <article className="flex flex-col overflow-hidden rounded-panel border border-border bg-white">
      {/* 1. 헤더 - "AI가 작성한 초안"임이 드러난다 (§9-3) */}
      <div className="flex flex-wrap items-start justify-between gap-x-3 gap-y-1 border-b border-border-soft px-6 py-[18px]">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2.5">
            <span className="font-mono text-caption font-extrabold text-primary">
              {candidate.id.toUpperCase()}
            </span>
            <span className="rounded-chip bg-warning-light px-2 py-[3px] text-[12.5px] font-bold text-warning">
              승인 대기
            </span>
            {draft.category && (
              <span className="rounded-chip bg-bg-sub px-2 py-[3px] text-[12.5px] font-bold text-text-sub">
                분야&ensp;{CATEGORY_LABEL[draft.category]}
              </span>
            )}
          </div>
          <h2 className="mt-2 text-card-title font-extrabold text-text">
            {candidate.title}
          </h2>
        </div>
        <span className="text-table-head whitespace-nowrap text-text-faint">
          AI 초안 생성 {formatDateTime(candidate.created_at)}
        </span>
      </div>

      {/* 2. 본문 */}
      <div className="flex flex-col gap-[18px] p-6">
        {/* 발단이 된 실패 질문 - 상단 가로 요약 바 (§9-3) */}
        <div className="flex flex-col gap-2 rounded-cell border border-dashed border-border bg-bg-admin px-4 py-3.5">
          <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
            <span className="text-table-head font-extrabold tracking-[0.04em] text-text-sub">
              발단이 된 실패 질문 (마스킹됨)
            </span>
            <span className="flex flex-wrap gap-x-3 text-[12.5px] text-text-faint">
              {sourceFailure?.repeat_count && (
                <span>
                  최근 30일{" "}
                  <b className="text-text">{sourceFailure.repeat_count}회</b>{" "}
                  반복
                </span>
              )}
              <span>텍스트는 30일 후 자동 파기</span>
            </span>
          </div>
          {sourceFailure ? (
            <>
              <p className="text-[16px] leading-[1.5] text-text">
                {sourceFailure.masked_question ?? "보관 기간 경과 (질문 텍스트 파기됨)"}
              </p>
              <div className="flex flex-wrap items-center gap-2">
                {/* 사유 뱃지 한글화(최종 폴리시 9) - 파란 텍스트 금지 규칙 유지 */}
                <span className="rounded-chip bg-primary-light px-2 py-[3px] text-[12px] font-bold text-text">
                  {FALLBACK_CODE_LABEL[sourceFailure.fallback_code]}
                </span>
                {sourceFailure.category && (
                  <span className="rounded-chip bg-bg-sub px-2 py-[3px] text-[12px] font-bold text-text-sub">
                    {CATEGORY_LABEL[sourceFailure.category]}
                  </span>
                )}
                <span className="text-[12.5px] text-text-faint tabular-nums">
                  접수 {formatDateTime(sourceFailure.created_at)}
                </span>
                {(sourceFailure.masked_question ?? "").includes("*") && (
                  <span className="rounded-chip bg-bg-sub px-2 py-[3px] text-[12px] font-bold text-text-sub">
                    개인정보 마스킹됨
                  </span>
                )}
              </div>
            </>
          ) : (
            <p className="text-admin-body text-text-sub">
              원 실패 질문(ID: {candidate.source_failure_id})을 찾을 수
              없습니다.
            </p>
          )}
        </div>

        {/* AI 초안 정의 표 - 한국어 라벨 주 + 스키마명 병기 (§13-2) */}
        <dl
          aria-label="AI 초안 (KB 스키마)"
          className="overflow-hidden rounded-btn border border-border-soft"
        >
          <DraftRow label="분야" schema="category">
            {draft.category ? CATEGORY_LABEL[draft.category] : "미분류"}
          </DraftRow>
          <DraftRow label="예상 질문" schema="question_examples">
            <ul className="space-y-0.5">
              {draft.question_examples.map((q) => (
                <li key={q}>{q}</li>
              ))}
            </ul>
          </DraftRow>
          <DraftRow label="답변 요약" schema="answer_summary">
            {draft.answer_summary}
          </DraftRow>
          <DraftRow label="신청 절차" schema="procedure_steps">
            <ol className="list-inside list-decimal space-y-0.5">
              {draft.procedure_steps.map((s) => (
                <li key={s}>{s}</li>
              ))}
            </ol>
          </DraftRow>
          <DraftRow label="처리 기간" schema="processing_time">
            {draft.processing_time}
          </DraftRow>
          <DraftRow label="수수료" schema="fee">
            {draft.fee}
          </DraftRow>
          <DraftRow label="담당 연락처" schema="fallback_contact">
            {/* §13-1: 기관명/전화/운영시간 각 한 줄 */}
            <p className="font-semibold">{draft.fallback_contact.name}</p>
            <p>
              <a
                href={`tel:${draft.fallback_contact.phone.split(" ")[0]}`}
                className="text-primary underline hover:text-primary-dark"
              >
                {draft.fallback_contact.phone}
              </a>
            </p>
            <p>{draft.fallback_contact.hours}</p>
          </DraftRow>
          <DraftRow label="출처 URL" schema="source_url">
            {/* 검증 상태 표시 - 미검증 앰버 경고 (§9-3, 이 화면 유일한 강조 박스) */}
            <div className="flex items-start gap-2 rounded-btn-s bg-warning-light px-3 py-2.5">
              <svg
                aria-hidden="true"
                className="mt-0.5 h-4 w-4 shrink-0 text-warning"
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
              <p className="text-admin-body text-warning">
                <b className="font-bold">출처 URL 미검증</b>
                <br />
                승인 전 담당자가 공식 출처를 확인해야 합니다.
              </p>
            </div>
          </DraftRow>
        </dl>

        {/* 승인 전 확인 체크리스트 (§9-3) */}
        <div className="flex flex-col gap-2.5">
          <p className="text-table-head font-extrabold tracking-[0.04em] text-text-sub">
            승인 전 확인 체크리스트
          </p>
          <div className="grid gap-2 md:grid-cols-3">
            {CHECKLIST.map((label, i) => (
              <label
                key={label}
                className="flex min-h-11 cursor-pointer items-center gap-2 rounded-btn-s border border-border bg-white px-3 py-2.5 text-caption font-semibold text-text hover:border-primary"
              >
                <input
                  type="checkbox"
                  checked={checked.has(i)}
                  onChange={() =>
                    setChecked((prev) => {
                      const next = new Set(prev);
                      if (next.has(i)) next.delete(i);
                      else next.add(i);
                      return next;
                    })
                  }
                  className="h-[18px] w-[18px] shrink-0 accent-verify"
                />
                {label}
              </label>
            ))}
          </div>
        </div>
      </div>

      {/* 3. 판정 바 - 하단 고정, 문서 결재의 문법 (§9-3) */}
      <div className="border-t border-border-soft bg-admin-soft px-6 py-4">
        {!rejecting ? (
          /* 768px 미만: 세로 스택 + 전체 폭 버튼 (모바일 정비 5) */
          <div className="flex flex-col gap-3 md:flex-row md:flex-wrap md:items-center md:justify-between">
            <span className="text-caption text-text-sub">
              승인하면 이 문서는{" "}
              <b className="text-verify-dark">ACTIVE</b>가 되어 다음 시민
              답변부터 사용됩니다.
            </span>
            {/* 버튼 순서: 승인 왼쪽 / 반려 오른쪽 */}
            <div className="flex flex-col gap-2.5 md:flex-row">
              <button
                type="button"
                disabled={busy}
                onClick={() => onReview(candidate.id, "승인")}
                className="min-h-12 w-full rounded-btn bg-verify px-6 text-[16px] font-extrabold text-white hover:bg-verify-dark active:bg-verify-dark disabled:opacity-60 md:w-auto"
              >
                승인
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={() => setRejecting(true)}
                className="min-h-12 w-full rounded-btn border border-border bg-white px-5 text-[16px] font-bold text-text-sub hover:border-text-faint hover:text-text active:bg-bg-sub disabled:opacity-60 md:w-auto"
              >
                반려
              </button>
            </div>
          </div>
        ) : (
          /* 반려 사유 코드 선택 - 자유 텍스트 없음. 768px 미만은 세로 스택 +
             전체 폭 버튼, 768px 이상은 우측 정렬 유지 */
          <fieldset>
            <legend className="block w-full text-admin-body font-bold text-text md:ml-auto md:text-right">
              반려 사유를 선택해 주세요
            </legend>
            <div className="mt-2 flex flex-wrap gap-2 md:justify-end">
              {REJECT_REASONS.map(({ code, label }) => (
                <label
                  key={code}
                  className={`flex min-h-11 cursor-pointer items-center rounded-btn-s border px-3 text-admin-body ${
                    rejectReason === code
                      ? "border-primary bg-primary-light font-bold text-primary-dark"
                      : "border-border bg-white text-text hover:bg-bg-sub"
                  }`}
                >
                  <input
                    type="radio"
                    name={`reject-reason-${candidate.id}`}
                    value={code}
                    checked={rejectReason === code}
                    onChange={() => setRejectReason(code)}
                    className="sr-only"
                  />
                  {label}
                </label>
              ))}
            </div>
            <div className="mt-3 flex flex-col gap-2 md:flex-row md:justify-end">
              <button
                type="button"
                disabled={busy}
                onClick={() => {
                  setRejecting(false);
                  setRejectReason(null);
                }}
                className="min-h-11 w-full rounded-btn-s border border-border bg-white px-5 text-admin-body font-bold text-text-sub hover:bg-bg-sub active:bg-bg-sub md:w-auto"
              >
                취소
              </button>
              <button
                type="button"
                disabled={busy || rejectReason === null}
                onClick={() => {
                  if (rejectReason) onReview(candidate.id, "반려", rejectReason);
                }}
                className="min-h-11 w-full rounded-btn-s bg-danger px-5 text-admin-body font-bold text-white hover:opacity-90 active:opacity-90 disabled:opacity-60 md:w-auto"
              >
                반려 확정
              </button>
            </div>
          </fieldset>
        )}
      </div>
    </article>
  );
}
