"use client";

/**
 * KB 후보 상세 카드 - DESIGN.md v3 §9-3 (데모 #5의 클라이맥스), 계약 적응판.
 * 세로 3분할: 헤더(뱃지 + "AI 초안 생성" 시각) / 본문(발단 실패 질문 요약 바 →
 * AI 초안 정의 표 → 승인 전 확인 체크리스트) / 판정 바.
 * - 초안 필드 라벨은 한국어가 주 + 계약 스키마명 12px 모노 병기 (§13-2).
 * - 계약 적응:
 *   · 반려 사유 코드 → review_comment 자유 텍스트(1..1000) 필수 - 승인·반려 공통.
 *   · source_url은 계약상 생성 시점부터 https 필수 - "미검증(null)" 표현 대신
 *     승인 전 확인 체크리스트가 사람 판정을 담보한다.
 *   · 검수는 APPROVER 역할 + 작성자와 다른 계정에서만 (자기검수 금지).
 *   · data_origin=MOCK 후보는 ACTIVE 승인 불가 (계약 불변식).
 * - 승인 버튼은 verify 초록 채움 - 이 화면 유일한 초록 채움 버튼 (§2).
 * - 승인 직후: 완료형 전환 + 우상단 승인 스탬프 (§7-2 ③형).
 */
import { useState } from "react";
import type { components } from "../../../../../packages/shared-contracts/src/generated/api";
import type { AdminActor } from "@/lib/admin-api";
import { INTENT_LABEL, STORED_REASON_LABEL } from "@/lib/labels";

type FailedQuestion = components["schemas"]["FailedQuestion"];
type KBCandidateSummary = components["schemas"]["KBCandidateSummary"];
type ReviewDecision = components["schemas"]["CandidateReviewRequest"]["decision"];

/** §9-3 승인 전 확인 체크리스트 3항목 */
const CHECKLIST = ["출처 URL 접속 확인", "원문 대조", "연락처·운영시간 확인"];

function formatDateTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/**
 * AI 초안 정의 표의 한 행 - 라벨은 한국어가 주 + 계약 스키마명 모노 병기 (§13-2).
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
  actor,
  busy,
  justApproved,
  onReview,
  onNext,
}: {
  candidate: KBCandidateSummary;
  /** 발단이 된 실패 질문 - failed_question_id로 조회한 원본 (없으면 이력 미표시) */
  sourceFailure?: FailedQuestion;
  /** 현재 시연 actor - 검수 가능 여부(역할·자기검수) 판정 */
  actor: AdminActor;
  busy: boolean;
  /** 승인 직후 완료형 전환 + 스탬프 연출 (§9-3) */
  justApproved: boolean;
  onReview: (id: string, decision: ReviewDecision, reviewComment: string) => void;
  /** 완료형의 "다음 후보 보기 →" */
  onNext: () => void;
}) {
  const [reviewComment, setReviewComment] = useState("");
  const [rejecting, setRejecting] = useState(false);
  const [checked, setChecked] = useState<Set<number>>(new Set());

  const isOwnCandidate = candidate.created_by === actor.actorId;
  const canReview =
    actor.role === "APPROVER" &&
    candidate.status === "PENDING_APPROVAL" &&
    !isOwnCandidate;
  const canApprove = canReview && candidate.data_origin === "OFFICIAL";
  const hasComment = reviewComment.trim().length > 0;

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
            {candidate.approved_at
              ? candidate.approved_at.slice(0, 10)
              : ""}
          </span>
          <span className="text-[11px] font-bold text-verify-dark">
            {candidate.reviewed_by ?? actor.actorId}
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-2.5 pr-[130px]">
          <span className="rounded-chip bg-verify-light-2 px-2 py-[3px] text-[12.5px] font-extrabold text-verify-dark">
            ACTIVE
          </span>
          {candidate.activated_kb_id && (
            <span className="font-mono text-[12.5px] font-bold text-text-sub">
              KB {candidate.activated_kb_id.slice(0, 8).toUpperCase()}
            </span>
          )}
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
            <span className="rounded-chip bg-warning-light px-2 py-[3px] text-[12.5px] font-bold text-warning">
              승인 대기
            </span>
            <span className="rounded-chip bg-bg-sub px-2 py-[3px] text-[12.5px] font-bold text-text-sub">
              분야&ensp;{INTENT_LABEL[candidate.category]}
            </span>
            {candidate.data_origin === "MOCK" && (
              <span className="rounded-chip bg-bg-sub px-2 py-[3px] text-[12.5px] font-bold text-text-sub">
                시연용 샘플
              </span>
            )}
          </div>
          <h2 className="mt-2 text-card-title font-extrabold text-text">
            {candidate.title}
          </h2>
          <p className="mt-1 text-table-head text-text-sub">
            작성 {candidate.created_by}
          </p>
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
            <span className="text-[12.5px] text-text-faint">
              텍스트는 30일 후 자동 파기
            </span>
          </div>
          {sourceFailure ? (
            <>
              <p className="text-[16px] leading-[1.5] text-text">
                {sourceFailure.masked_question ??
                  "보관 기간 경과 (질문 텍스트 파기됨)"}
              </p>
              <div className="flex flex-wrap items-center gap-2">
                {/* 사유 뱃지 한글화(최종 폴리시 9) - 파란 텍스트 금지 규칙 유지 */}
                <span className="rounded-chip bg-primary-light px-2 py-[3px] text-[12px] font-bold text-text">
                  {STORED_REASON_LABEL[sourceFailure.fallback_reason]}
                </span>
                <span className="rounded-chip bg-bg-sub px-2 py-[3px] text-[12px] font-bold text-text-sub">
                  {INTENT_LABEL[sourceFailure.intent]}
                </span>
                <span className="text-[12.5px] text-text-faint tabular-nums">
                  접수 {formatDateTime(sourceFailure.created_at)}
                </span>
              </div>
            </>
          ) : (
            <p className="text-admin-body text-text-sub">
              원 실패 질문(ID: {candidate.failed_question_id})을 찾을 수
              없습니다.
            </p>
          )}
        </div>

        {/* AI 초안 정의 표 - 한국어 라벨 주 + 계약 스키마명 병기 (§13-2) */}
        <dl
          aria-label="AI 초안 (KB 후보 스키마)"
          className="overflow-hidden rounded-btn border border-border-soft"
        >
          <DraftRow label="분야" schema="category">
            {INTENT_LABEL[candidate.category]}
          </DraftRow>
          <DraftRow label="대표 질문" schema="representative_question">
            {candidate.representative_question}
          </DraftRow>
          <DraftRow label="답변 요약" schema="answer_summary">
            {candidate.answer_summary}
          </DraftRow>
          {candidate.procedure_steps.length > 0 && (
            <DraftRow label="신청 절차" schema="procedure_steps">
              <ol className="list-inside list-decimal space-y-0.5">
                {candidate.procedure_steps.map((s) => (
                  <li key={s}>{s}</li>
                ))}
              </ol>
            </DraftRow>
          )}
          {candidate.required_documents.length > 0 && (
            <DraftRow label="필요 서류" schema="required_documents">
              <ul className="space-y-0.5">
                {candidate.required_documents.map((docItem) => (
                  <li key={docItem}>{docItem}</li>
                ))}
              </ul>
            </DraftRow>
          )}
          <DraftRow label="처리 기간" schema="processing_time">
            {candidate.processing_time ?? "별도 표기 없음"}
          </DraftRow>
          <DraftRow label="수수료" schema="fee">
            {candidate.fee ?? "별도 표기 없음"}
          </DraftRow>
          <DraftRow label="담당 부서" schema="department">
            {candidate.department}
          </DraftRow>
          {candidate.caution && (
            <DraftRow label="주의사항" schema="caution">
              {candidate.caution}
            </DraftRow>
          )}
          <DraftRow label="출처" schema="source_url">
            <p>
              <a
                href={candidate.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary underline hover:text-primary-dark"
              >
                {candidate.source_title}
              </a>
            </p>
            <p className="mt-0.5 text-[13px] text-text-sub">
              공식 확인일{" "}
              <time dateTime={candidate.last_verified_at}>
                {candidate.last_verified_at}
              </time>
            </p>
            {/* 사람 판정의 물증 - 승인 전 담당자 확인 경고 (§9-3) */}
            <div className="mt-2 flex items-start gap-2 rounded-btn-s bg-warning-light px-3 py-2.5">
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
                <b className="font-bold">AI가 작성한 초안입니다</b>
                <br />
                승인 전 담당자가 공식 출처를 직접 확인해야 합니다.
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
        {actor.role !== "APPROVER" ? (
          <p className="text-caption text-text-sub">
            검수·판정은 <b className="font-bold">별도 승인자(APPROVER)</b> 역할에서
            할 수 있습니다. 좌측 시연 역할을 전환하세요.
          </p>
        ) : isOwnCandidate ? (
          <p className="text-caption text-text-sub">
            작성자와 검수자가 같아 검수할 수 없습니다 (자기검수 금지).
          </p>
        ) : (
          <div className="flex flex-col gap-3">
            {candidate.data_origin === "MOCK" && (
              <p className="text-caption text-text-sub">
                시연용 샘플(MOCK)은 ACTIVE로 승인할 수 없습니다. 반려만
                가능합니다.
              </p>
            )}
            {/* 계약: 승인·반려 모두 review_comment(자유 텍스트 1..1000) 필수 */}
            <div>
              <label
                htmlFor={`review-comment-${candidate.id}`}
                className="mb-1.5 block text-admin-body font-bold text-text"
              >
                검수 의견 (필수)
              </label>
              <textarea
                id={`review-comment-${candidate.id}`}
                rows={3}
                maxLength={1000}
                value={reviewComment}
                onChange={(event) => setReviewComment(event.target.value)}
                placeholder="확인한 출처와 판정 근거를 남겨 주세요"
                className="w-full rounded-btn border border-border bg-white px-3.5 py-2.5 text-admin-body text-text placeholder:text-text-faint focus:border-primary"
              />
            </div>
            {!rejecting ? (
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
                    disabled={busy || !canApprove || !hasComment}
                    onClick={() =>
                      onReview(candidate.id, "APPROVED", reviewComment.trim())
                    }
                    className="min-h-12 w-full rounded-btn bg-verify px-6 text-[16px] font-extrabold text-white hover:bg-verify-dark active:bg-verify-dark disabled:opacity-60 md:w-auto"
                  >
                    승인하고 ACTIVE 반영
                  </button>
                  <button
                    type="button"
                    disabled={busy || !canReview || !hasComment}
                    onClick={() => setRejecting(true)}
                    className="min-h-12 w-full rounded-btn border border-border bg-white px-5 text-[16px] font-bold text-text-sub hover:border-text-faint hover:text-text active:bg-bg-sub disabled:opacity-60 md:w-auto"
                  >
                    반려
                  </button>
                </div>
              </div>
            ) : (
              /* 반려 확정 - 빨강은 반려 확정에만 (§2) */
              <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-end">
                <span className="text-admin-body font-bold text-text">
                  이 후보를 반려할까요? 검수 의견이 반려 사유로 기록됩니다.
                </span>
                <div className="flex flex-col gap-2 md:flex-row">
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => setRejecting(false)}
                    className="min-h-11 w-full rounded-btn-s border border-border bg-white px-5 text-admin-body font-bold text-text-sub hover:bg-bg-sub active:bg-bg-sub md:w-auto"
                  >
                    취소
                  </button>
                  <button
                    type="button"
                    disabled={busy || !hasComment}
                    onClick={() =>
                      onReview(candidate.id, "REJECTED", reviewComment.trim())
                    }
                    className="min-h-11 w-full rounded-btn-s bg-danger px-5 text-admin-body font-bold text-white hover:opacity-90 active:opacity-90 disabled:opacity-60 md:w-auto"
                  >
                    반려 확정
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </article>
  );
}
