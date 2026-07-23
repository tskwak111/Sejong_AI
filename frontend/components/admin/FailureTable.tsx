"use client";

/**
 * 실패 질문 큐 - DESIGN.md v3 §9-2 + 이음센터 모바일 정비 4.
 * - 768px 이상: 테이블 현행 유지. 열 = 접수 / 질문(마스킹) / 폴백 사유 / 분야 /
 *   상태 / 작업. 헤더 13px 800 text-sub + admin-soft 배경, 행 hover card-head.
 * - 768px 미만: 세로 카드 리스트로 재조립 (가로 스크롤 금지) -
 *   1행 질문(semibold, 미보관 건은 조립 제목 + 태그) / 2행 접수일 + 사유 뱃지 +
 *   분야(여백 구분) / 3행 상태 뱃지 좌 + 작업 버튼 우. 카드 사이 8px,
 *   신규 도착 하이라이트 펄스는 카드 배경으로 동일 적용.
 * - 폴백 사유 = 모노 코드 뱃지. 파란 텍스트 금지 규칙 유지(text 색 + primary-light 배경).
 * - 상태 뱃지 = §10 색 규칙 (신규=warning / 검토 중=primary / 처리 완료=verify).
 * - "KB 후보 초안 생성"은 INSUFFICIENT_GROUNDING 행에만.
 *   처리 완료된 비ISG 행은 처리 노트 텍스트만.
 * - masked_question NULL 행도 깨지지 않게 - ISG="보관 기간 경과", 비ISG="텍스트 미보관".
 * - 상태 전이는 단방향: 신규 → 검토중 → 처리완료 (되돌리기는 P0 범위 밖)
 */
import type { FailureQueueItem, FailureStatus } from "@/types/api";
import { CATEGORY_LABEL, FALLBACK_CODE_LABEL } from "@/types/api";

/** §10 상태 뱃지 색 규칙 - 대기=warning / 진행=primary / 완료=verify */
const STATUS_BADGE: Record<FailureStatus, string> = {
  신규: "bg-warning-light text-warning",
  검토중: "bg-primary-light text-primary",
  처리완료: "bg-verify-light-2 text-verify-dark",
};

/** 화면 표시 라벨 - 내부 상태값(enum)과 분리, 전 화면 표기 통일 */
const STATUS_LABEL: Record<FailureStatus, string> = {
  신규: "신규",
  검토중: "검토 중",
  처리완료: "처리 완료",
};

/** 다음 처리 상태 (단방향) */
const NEXT_STATUS: Partial<Record<FailureStatus, FailureStatus>> = {
  신규: "검토중",
  검토중: "처리완료",
};

const NEXT_STATUS_LABEL: Partial<Record<FailureStatus, string>> = {
  신규: "검토 시작",
  검토중: "처리 완료로 변경",
};

function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/** NULL 파기/미보관 행의 대체 문구 - ISG의 null = 30일 파기, 비ISG = 미보관 (§9-2) */
function nullNote(item: FailureQueueItem): string {
  return item.fallback_code === "INSUFFICIENT_GROUNDING"
    ? "보관 기간 경과 (질문 텍스트 파기됨)"
    : "텍스트 미보관 (분야와 사유만 집계)";
}

/** §9-2 하단 캡션 - 저장 정책 안내 (테이블·카드 리스트 공용 문구) */
const POLICY_CAPTION =
  "개인별 조회, 법적 판단, 지원 범위 밖 실패는 질문 텍스트를 저장하지 않고 분야와 사유만 집계합니다.";

export default function FailureTable({
  items,
  draftedFailureIds,
  busyId,
  highlightIds,
  onChangeStatus,
  onCreateDraft,
}: {
  items: FailureQueueItem[];
  /** 이미 KB 후보 초안이 생성된 실패 건 id 집합 - 중복 생성 방지 */
  draftedFailureIds: Set<string>;
  /** 처리 중인 행 id (버튼 비활성) */
  busyId: string | null;
  /** 새로고침 후 새로 등장한 행 - highlight 배경에서 2초 페이드 (§9-2) */
  highlightIds?: Set<string>;
  onChangeStatus: (id: string, status: FailureStatus) => void;
  onCreateDraft: (id: string) => void;
}) {
  return (
    <>
      {/* ── 768px 미만: 세로 카드 리스트 (모바일 정비 4) ── */}
      <div className="flex flex-col gap-2 md:hidden">
        {items.map((item) => {
          const next = NEXT_STATUS[item.status];
          const busy = busyId === item.id;
          const drafted = draftedFailureIds.has(item.id);
          const isIsg = item.fallback_code === "INSUFFICIENT_GROUNDING";
          return (
            <article
              key={item.id}
              className={`flex flex-col gap-2.5 rounded-card-s border border-border bg-white p-4 ${
                highlightIds?.has(item.id) ? "row-highlight" : ""
              }`}
            >
              {/* 1행: 질문 - 미보관 건은 분야·사유로 조립한 제목 + 태그 */}
              {item.masked_question !== null ? (
                <p className="text-note leading-[1.45] font-semibold text-text">
                  {item.masked_question}
                </p>
              ) : (
                <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-note leading-[1.45] font-semibold text-text-sub">
                  {item.category ? CATEGORY_LABEL[item.category] : "기타"}{" "}
                  {FALLBACK_CODE_LABEL[item.fallback_code]} 실패
                  <span className="rounded-chip bg-bg-sub px-2 py-[3px] text-[12px] font-bold text-text-sub">
                    {isIsg ? "보관 기간 경과" : "텍스트 미보관"}
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
                  {FALLBACK_CODE_LABEL[item.fallback_code]}
                </span>
                <span className="text-[13.5px] font-bold text-text-sub">
                  {item.category ? CATEGORY_LABEL[item.category] : "미분류"}
                </span>
              </div>
              {/* 3행: 상태 뱃지 좌 + 작업 버튼 우 (터치 44px) */}
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span
                  className={`rounded-chip px-2 py-[3px] text-[12.5px] font-extrabold ${STATUS_BADGE[item.status]}`}
                >
                  {STATUS_LABEL[item.status]}
                </span>
                <div className="flex flex-wrap justify-end gap-2">
                  {next && (
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => onChangeStatus(item.id, next)}
                      className="min-h-11 rounded-btn-s border border-border bg-white px-3 text-[13.5px] font-bold text-text-sub hover:border-text-faint hover:text-text active:bg-bg-sub disabled:opacity-60"
                    >
                      {NEXT_STATUS_LABEL[item.status]}
                    </button>
                  )}
                  {isIsg && item.status !== "처리완료" && (
                    <button
                      type="button"
                      disabled={busy || drafted}
                      onClick={() => onCreateDraft(item.id)}
                      className="min-h-11 rounded-btn-s border border-primary bg-white px-3 text-[13.5px] font-bold text-primary hover:bg-primary-light active:bg-primary-light disabled:opacity-60"
                    >
                      {drafted ? "초안 생성됨" : "KB 후보 생성"}
                    </button>
                  )}
                  {/* 처리 완료된 비ISG 건 - 처리 노트 텍스트만 (§9-2) */}
                  {!isIsg && item.status === "처리완료" && (
                    <span className="text-[13.5px] text-text-faint">
                      {item.fallback_code === "OUT_OF_SCOPE"
                        ? "집계만 유지"
                        : "담당 연결 완료"}
                    </span>
                  )}
                </div>
              </div>
            </article>
          );
        })}
        <p className="px-1 text-[13.5px] leading-[1.5] text-text-faint">
          {POLICY_CAPTION}
        </p>
      </div>

      {/* ── 768px 이상: 테이블 현행 유지 ── */}
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
                폴백 사유
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
            {items.map((item) => {
              const next = NEXT_STATUS[item.status];
              const busy = busyId === item.id;
              const drafted = draftedFailureIds.has(item.id);
              const isIsg = item.fallback_code === "INSUFFICIENT_GROUNDING";
              return (
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
                      <span className="text-text-faint">{nullNote(item)}</span>
                    )}
                  </td>
                  {/* 사유 뱃지 한글화(최종 폴리시 9) - 파란 텍스트 금지 규칙 유지 */}
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span className="inline-flex items-center rounded-chip bg-primary-light px-2 py-[3px] text-[11.5px] font-bold text-text">
                      {FALLBACK_CODE_LABEL[item.fallback_code]}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-[13.5px] font-bold whitespace-nowrap text-text-sub">
                    {item.category ? CATEGORY_LABEL[item.category] : "미분류"}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span
                      className={`inline-flex items-center rounded-chip px-2 py-[3px] text-[12.5px] font-extrabold ${STATUS_BADGE[item.status]}`}
                    >
                      {STATUS_LABEL[item.status]}
                    </span>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <div className="flex items-center gap-2">
                      {next && (
                        <button
                          type="button"
                          disabled={busy}
                          onClick={() => onChangeStatus(item.id, next)}
                          className="min-h-[38px] rounded-btn-s border border-border bg-white px-3 text-[13.5px] font-bold text-text-sub hover:border-text-faint hover:text-text active:bg-bg-sub disabled:opacity-60"
                        >
                          {NEXT_STATUS_LABEL[item.status]}
                        </button>
                      )}
                      {isIsg && item.status !== "처리완료" && (
                        <button
                          type="button"
                          disabled={busy || drafted}
                          onClick={() => onCreateDraft(item.id)}
                          className="min-h-[38px] rounded-btn-s border border-primary bg-white px-3 text-[13.5px] font-bold text-primary hover:bg-primary-light active:bg-primary-light disabled:opacity-60"
                        >
                          {drafted ? "초안 생성됨" : "KB 후보 생성"}
                        </button>
                      )}
                      {/* 처리 완료된 비ISG 행 - 처리 노트 텍스트만 (§9-2) */}
                      {!isIsg && item.status === "처리완료" && (
                        <span className="text-[13.5px] text-text-faint">
                          {item.fallback_code === "OUT_OF_SCOPE"
                            ? "집계만 유지"
                            : "담당 연결 완료"}
                        </span>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
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
