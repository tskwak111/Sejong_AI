"use client";

/**
 * 실패 질문 큐 - DESIGN.md v3 §9-2 + 이음센터 모바일 정비 4, 계약 적응판.
 * - 768px 이상: 테이블. 열 = 접수 / 질문(마스킹) / 저장 사유 / 분야 / 상태 / 작업.
 * - 768px 미만: 세로 카드 리스트 (가로 스크롤 금지).
 * - 계약 FailedQuestion 기준:
 *   상태 2단계 NEW(신규) → REASON_CONFIRMED(사유 확정, PATCH /reason).
 *   저장 사유는 StoredFailureReason 3종 - OUT_OF_SCOPE는 행이 생성되지 않는다.
 *   masked_question NULL = 30일 보관 기간 경과 파기 (text_purged_at 기록) -
 *   NULL 행도 깨지지 않게 렌더링한다.
 * - "KB 후보 생성"은 candidate_eligible(근거 부족)이며 사유 확정된 행에만.
 */
import type { components } from "../../../../../packages/shared-contracts/src/generated/api";
import { INTENT_LABEL, STORED_REASON_LABEL } from "@/lib/labels";

type FailedQuestion = components["schemas"]["FailedQuestion"];
type FailedQuestionStatus = FailedQuestion["status"];

/** §10 상태 뱃지 색 규칙 - 대기=warning / 완료=verify */
const STATUS_BADGE: Record<FailedQuestionStatus, string> = {
  NEW: "bg-warning-light text-warning",
  REASON_CONFIRMED: "bg-verify-light-2 text-verify-dark",
};

/** 화면 표시 라벨 - 내부 상태값(enum)과 분리, 전 화면 표기 통일 */
const STATUS_LABEL: Record<FailedQuestionStatus, string> = {
  NEW: "신규",
  REASON_CONFIRMED: "사유 확정",
};

function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/** §9-2 하단 캡션 - 저장 정책 안내 (계약 문구로 갱신) */
const POLICY_CAPTION =
  "질문 텍스트는 마스킹 후 30일 보관 뒤 파기됩니다. 지원 범위 밖 질문은 실패 큐에 저장되지 않습니다.";

const PURGED_NOTE = "보관 기간 경과 (질문 텍스트 파기됨)";

export default function FailureTable({
  items,
  draftedFailureIds,
  busyId,
  highlightIds,
  canOperate,
  onConfirmReason,
  onCreateDraft,
}: {
  items: FailedQuestion[];
  /** 이미 KB 후보가 생성된 실패 건 id 집합 - 중복 생성 방지 (계약 409) */
  draftedFailureIds: Set<string>;
  /** 처리 중인 행 id (버튼 비활성) */
  busyId: string | null;
  /** 새로고침 후 새로 등장한 행 - highlight 배경에서 2초 페이드 (§9-2) */
  highlightIds?: Set<string>;
  /** OPERATOR 역할일 때만 작성 액션 노출 (X-Demo-Role) */
  canOperate: boolean;
  onConfirmReason: (id: string) => void;
  onCreateDraft: (id: string) => void;
}) {
  const actionsFor = (item: FailedQuestion, dense: boolean) => {
    const busy = busyId === item.id;
    const drafted = draftedFailureIds.has(item.id);
    const buttonBase = dense ? "min-h-[38px]" : "min-h-11";
    return (
      <div className="flex flex-wrap items-center justify-end gap-2 md:justify-start">
        {canOperate && item.status === "NEW" && (
          <button
            type="button"
            disabled={busy}
            onClick={() => onConfirmReason(item.id)}
            className={`${buttonBase} rounded-btn-s border border-border bg-white px-3 text-[13.5px] font-bold text-text-sub hover:border-text-faint hover:text-text active:bg-bg-sub disabled:opacity-60`}
          >
            사유 확정
          </button>
        )}
        {canOperate &&
          item.status === "REASON_CONFIRMED" &&
          item.candidate_eligible &&
          item.masked_question !== null && (
            <button
              type="button"
              disabled={busy || drafted}
              onClick={() => onCreateDraft(item.id)}
              className={`${buttonBase} rounded-btn-s border border-primary bg-white px-3 text-[13.5px] font-bold text-primary hover:bg-primary-light active:bg-primary-light disabled:opacity-60`}
            >
              {drafted ? "초안 생성됨" : "KB 후보 생성"}
            </button>
          )}
        {/* 텍스트가 파기된 대상 행 - 대표 질문을 만들 수 없어 초안 작성 불가 */}
        {item.status === "REASON_CONFIRMED" &&
          item.candidate_eligible &&
          item.masked_question === null && (
            <span className="text-[13.5px] text-text-faint">
              텍스트 파기로 후보 작성 불가
            </span>
          )}
        {/* 사유 확정된 비대상(근거 부족 아님) 행 - 처리 노트 텍스트만 (§9-2) */}
        {item.status === "REASON_CONFIRMED" && !item.candidate_eligible && (
          <span className="text-[13.5px] text-text-faint">담당 연결 완료</span>
        )}
        {!canOperate && item.status === "NEW" && (
          <span className="text-[13.5px] text-text-faint">
            작성 운영자 역할에서 처리
          </span>
        )}
      </div>
    );
  };

  return (
    <>
      {/* ── 768px 미만: 세로 카드 리스트 (모바일 정비 4) ── */}
      <div className="flex flex-col gap-2 md:hidden">
        {items.map((item) => (
          <article
            key={item.id}
            className={`flex flex-col gap-2.5 rounded-card-s border border-border bg-white p-4 ${
              highlightIds?.has(item.id) ? "row-highlight" : ""
            }`}
          >
            {/* 1행: 질문 - 파기 행은 대체 문구 + 태그 */}
            {item.masked_question !== null ? (
              <p className="text-note leading-[1.45] font-semibold text-text">
                {item.masked_question}
              </p>
            ) : (
              <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-note leading-[1.45] font-semibold text-text-sub">
                {INTENT_LABEL[item.intent]}{" "}
                {STORED_REASON_LABEL[item.fallback_reason]} 실패
                <span className="rounded-chip bg-bg-sub px-2 py-[3px] text-[12px] font-bold text-text-sub">
                  보관 기간 경과
                </span>
              </p>
            )}
            {/* 2행: 접수일 + 사유 뱃지 + 분야 - 여백 구분 (§13-1) */}
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <span className="text-[13.5px] text-text-faint tabular-nums">
                {formatDate(item.created_at)}
              </span>
              {/* 최종 폴리시 9: 사유 뱃지 한글화 (영문 코드 미표시) */}
              <span className="rounded-chip bg-primary-light px-2 py-[3px] text-[11.5px] font-bold text-text">
                {STORED_REASON_LABEL[item.fallback_reason]}
              </span>
              <span className="text-[13.5px] font-bold text-text-sub">
                {INTENT_LABEL[item.intent]}
              </span>
            </div>
            {/* 3행: 상태 뱃지 좌 + 작업 버튼 우 (터치 44px) */}
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span
                className={`rounded-chip px-2 py-[3px] text-[12.5px] font-extrabold ${STATUS_BADGE[item.status]}`}
              >
                {STATUS_LABEL[item.status]}
              </span>
              {actionsFor(item, false)}
            </div>
          </article>
        ))}
        <p className="px-1 text-[13.5px] leading-[1.5] text-text-faint">
          {POLICY_CAPTION}
        </p>
      </div>

      {/* ── 768px 이상: 테이블 ── */}
      <div className="hidden overflow-x-auto rounded-panel border border-border bg-white md:block">
        <table className="w-full min-w-[860px] border-collapse text-left">
          <thead>
            <tr className="border-b border-border-soft bg-admin-soft">
              <th className="px-4 py-3 text-table-head font-extrabold text-text-sub">
                접수
              </th>
              <th className="px-4 py-3 text-table-head font-extrabold text-text-sub">
                질문 (마스킹)
              </th>
              <th className="px-4 py-3 text-table-head font-extrabold text-text-sub">
                저장 사유
              </th>
              <th className="px-4 py-3 text-table-head font-extrabold text-text-sub">
                분야
              </th>
              <th className="px-4 py-3 text-table-head font-extrabold text-text-sub">
                상태
              </th>
              <th className="px-4 py-3 text-table-head font-extrabold text-text-sub">
                작업
              </th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr
                key={item.id}
                className={`border-b border-border-soft last:border-b-0 hover:bg-card-head ${
                  highlightIds?.has(item.id) ? "row-highlight" : ""
                }`}
              >
                <td className="px-4 py-3 text-[13.5px] whitespace-nowrap text-text-faint tabular-nums">
                  {formatDate(item.created_at)}
                </td>
                <td className="max-w-[320px] px-4 py-3 text-admin-body text-text">
                  {item.masked_question ?? (
                    <span className="text-text-faint">{PURGED_NOTE}</span>
                  )}
                </td>
                {/* 사유 뱃지 한글화(최종 폴리시 9) - 파란 텍스트 금지 규칙 유지 */}
                <td className="px-4 py-3 whitespace-nowrap">
                  <span className="inline-flex items-center rounded-chip bg-primary-light px-2 py-[3px] text-[11.5px] font-bold text-text">
                    {STORED_REASON_LABEL[item.fallback_reason]}
                  </span>
                </td>
                <td className="px-4 py-3 text-[13.5px] font-bold whitespace-nowrap text-text-sub">
                  {INTENT_LABEL[item.intent]}
                </td>
                <td className="px-4 py-3 whitespace-nowrap">
                  <span
                    className={`inline-flex items-center rounded-chip px-2 py-[3px] text-[12.5px] font-extrabold ${STATUS_BADGE[item.status]}`}
                  >
                    {STATUS_LABEL[item.status]}
                  </span>
                </td>
                <td className="px-4 py-3 whitespace-nowrap">
                  {actionsFor(item, true)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {/* §9-2 테이블 하단 캡션 - 저장 정책 안내 */}
        <div className="border-t border-border-soft bg-admin-soft px-5 py-3 text-[13.5px] text-text-faint">
          {POLICY_CAPTION}
        </div>
      </div>
    </>
  );
}
