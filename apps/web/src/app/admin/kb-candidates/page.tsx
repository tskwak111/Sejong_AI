"use client";

/**
 * KB 후보 승인 - CLAUDE.md §6 (3) + DESIGN.md v3 §9-3, 계약 적응판.
 * - 레이아웃: 좌측 승인 대기 목록 300px(카드형) + 우측 상세 카드.
 * - 상태(계약): DRAFTED → PENDING_APPROVAL → APPROVED / REJECTED.
 *   생성 화면(실패 질문 관리)에서 초안 생성 시 승인 요청까지 이어지므로
 *   이 화면은 승인 대기(PENDING_APPROVAL) 판정에 집중한다.
 * - 검수는 APPROVER 역할 + 작성자와 다른 계정에서만. review_comment 필수.
 * - 승인 직후 상세 카드가 완료형(ACTIVE + 승인 스탬프)으로 전환 + 토스트 병행.
 * - 실패 질문을 함께 조회해 후보별 "발단이 된 실패 질문" 이력을 표시.
 */
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import type { components } from "../../../../../../packages/shared-contracts/src/generated/api";
import { useAdmin } from "@/components/admin/AdminShell";
import KbCandidateReview from "@/components/admin/KbCandidateReview";
import EmptyState from "@/components/admin/EmptyState";
import PageHeader from "@/components/admin/PageHeader";
import Toast from "@/components/common/Toast";

type FailedQuestion = components["schemas"]["FailedQuestion"];
type KBCandidateSummary = components["schemas"]["KBCandidateSummary"];
type ReviewDecision = components["schemas"]["CandidateReviewRequest"]["decision"];
type CandidateStatus = components["schemas"]["KBCandidateStatus"];

const STATUS_FILTERS: ReadonlyArray<{ value: CandidateStatus; label: string }> = [
  { value: "DRAFTED", label: "작성 중" },
  { value: "PENDING_APPROVAL", label: "승인 대기" },
  { value: "APPROVED", label: "승인 완료" },
  { value: "REJECTED", label: "반려" },
];

export default function AdminKbCandidatesPage() {
  const { transport, actor, role, mode, notifyDataChanged } = useAdmin();
  const [items, setItems] = useState<KBCandidateSummary[] | null>(null);
  const [failures, setFailures] = useState<Map<string, FailedQuestion>>(
    new Map(),
  );
  const [busyId, setBusyId] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [justApprovedId, setJustApprovedId] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] =
    useState<CandidateStatus>("PENDING_APPROVAL");

  // setState는 조회 완료 콜백에서만 - 이펙트 본문 동기 setState 금지 규칙 준수
  const fetchData = useCallback(
    () =>
      Promise.all([
        transport.listCandidates(actor),
        transport.listFailedQuestions(actor),
      ])
        .then(([candidateResponse, failureResponse]) => {
          const list = [...candidateResponse.items];
          // 승인 대기 우선 + 최신순
          list.sort((a, b) => {
            const aPending = a.status === "PENDING_APPROVAL";
            const bPending = b.status === "PENDING_APPROVAL";
            if (aPending !== bPending) return aPending ? -1 : 1;
            return b.created_at.localeCompare(a.created_at);
          });
          setItems(list);
          setFailures(new Map(failureResponse.items.map((f) => [f.id, f])));
          setLastUpdated(new Date());
        })
        .catch(() => {
          setToast("운영 데이터를 불러오지 못했어요. 잠시 후 다시 시도해 주세요.");
        }),
    [actor, transport],
  );

  /** 새로고침 버튼·판정 후 재조회 - 진행 표시 포함 */
  const load = useCallback(async () => {
    setRefreshing(true);
    try {
      await fetchData();
    } finally {
      setRefreshing(false);
    }
  }, [fetchData]);

  useEffect(() => {
    void fetchData();
  }, [fetchData]);

  const review = async (
    id: string,
    decision: ReviewDecision,
    reviewComment: string,
  ) => {
    setBusyId(id);
    try {
      await transport.reviewCandidate(actor, id, {
        decision,
        review_comment: reviewComment,
      });
      if (decision === "APPROVED") {
        // 승인 직후 완료형 + 스탬프 연출 (§9-3) - 선택 유지
        setSelectedId(id);
        setJustApprovedId(id);
        setToast("KB 문서가 ACTIVE로 반영되었습니다");
      } else {
        // 반려된 후보는 대기 목록에서 빠진다 - 다음 대기 건으로 선택 이동
        setJustApprovedId(null);
        setSelectedId(null);
        setToast("후보가 반려되었습니다");
      }
      await load();
      notifyDataChanged();
    } catch {
      setToast("검수 결과를 반영하지 못했어요. 입력값을 확인해 주세요.");
    } finally {
      setBusyId(null);
    }
  };

  const pending = (items ?? []).filter((c) => c.status === "PENDING_APPROVAL");
  const pendingCount = pending.length;
  const filteredHistory = (items ?? []).filter((item) => item.status === statusFilter);

  // 선택된 후보 - 명시 선택이 없으면 대기 목록 첫 건.
  // 판정이 끝난 후보는 승인 직후 완료형(justApproved)일 때만 상세에 남는다.
  const selected =
    (items ?? []).find(
      (c) =>
        c.id === selectedId &&
        (c.status === "PENDING_APPROVAL" || c.id === justApprovedId),
    ) ??
    pending[0] ??
    null;

  /** 완료형의 "다음 후보 보기 →" - 다음 대기 건으로 전환 */
  const goNext = () => {
    setJustApprovedId(null);
    setSelectedId(
      pending.find((c) => c.id !== justApprovedId)?.id ?? null,
    );
  };

  /** 대기 목록 카드의 메타 - 출처·데이터 성격 (§9-3) */
  const cardMeta = (c: KBCandidateSummary): string[] => [
    c.data_origin === "OFFICIAL" ? "공식 출처 기반" : "시연용 샘플",
    `작성 ${c.created_by}`,
  ];

  return (
    <main id="main" tabIndex={-1}>
      <PageHeader
        title="KB 후보 승인"
        subtitle={
          <>
            <span>운영자가 공식 출처를 확인해 작성한 KB 후보</span>
            <span>별도 승인자가 승인하면 ACTIVE로 반영</span>
          </>
        }
        meta={
          <>
            {items !== null && (
              <span className="text-caption text-text-sub">
                승인 대기{" "}
                <b className="text-[16px] font-extrabold text-primary tabular-nums">
                  {pendingCount}
                </b>
                건
              </span>
            )}
            {/* 담당자 표시 (§5-2) - 현재 시연 actor */}
            <span className="flex items-center gap-2 rounded-pill bg-bg-sub px-3.5 py-1.5">
              <svg
                aria-hidden="true"
                className="h-4 w-4 shrink-0 text-text-sub"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth={2}
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <circle cx="12" cy="8" r="4" />
                <path d="M4 20c0-3.3 3.6-5.5 8-5.5s8 2.2 8 5.5" />
              </svg>
              <span className="text-caption font-bold text-text">
                {role === "APPROVER" ? "별도 승인자" : "작성 운영자"} ·{" "}
                {actor.actorId}
              </span>
            </span>
          </>
        }
        lastUpdated={lastUpdated}
        refreshing={refreshing}
        onRefresh={() => void load()}
      />

      <div className="px-5 py-[22px] md:px-7">
        {items !== null && (
          <div
            role="group"
            aria-label="KB 후보 상태"
            className="mb-4 flex gap-2 overflow-x-auto pb-1"
          >
            {STATUS_FILTERS.map(({ value, label }) => (
              <button
                key={value}
                type="button"
                aria-pressed={statusFilter === value}
                onClick={() => {
                  setStatusFilter(value);
                  setSelectedId(null);
                  setJustApprovedId(null);
                }}
                className={`min-h-11 shrink-0 rounded-pill px-4 text-note font-bold ${
                  statusFilter === value
                    ? "bg-primary text-white"
                    : "border border-border bg-white text-text-sub"
                }`}
              >
                {label} {items.filter((item) => item.status === value).length}
              </button>
            ))}
          </div>
        )}
        {items === null ? (
          <p className="text-admin-body text-text-sub">불러오는 중…</p>
        ) : items.length === 0 ? (
          <EmptyState
            title="검토할 KB 후보가 없습니다"
            description="실패 질문 관리에서 '근거 부족' 건에 대해 KB 후보 초안을 생성하면 이 목록에 올라옵니다."
            action={
              <Link
                href="/admin/failures"
                className="inline-flex min-h-11 items-center rounded-btn-s border border-primary bg-white px-4 text-admin-body font-bold text-primary hover:bg-primary-light active:bg-primary-light"
              >
                실패 질문 관리로 이동
              </Link>
            }
          />
        ) : statusFilter !== "PENDING_APPROVAL" ? (
          filteredHistory.length === 0 ? (
            <p className="rounded-card-s border border-border bg-white px-4 py-4 text-caption text-text-sub">
              이 상태의 KB 후보가 없습니다.
            </p>
          ) : (
            <ul className="grid gap-3">
              {filteredHistory.map((candidate) => (
                <li
                  key={candidate.id}
                  className="rounded-card-s border border-border bg-white p-4"
                >
                  <p className="text-admin-body font-extrabold text-text">
                    {candidate.title}
                  </p>
                  <p className="mt-1 text-caption text-text-sub">
                    작성 {candidate.created_by}
                    {candidate.reviewed_by
                      ? ` · 검수 ${candidate.reviewed_by}`
                      : ""}
                  </p>
                  {candidate.review_comment && (
                    <p className="mt-2 text-note text-text">
                      검수 의견: {candidate.review_comment}
                    </p>
                  )}
                </li>
              ))}
            </ul>
          )
        ) : (
          <div className="flex flex-col gap-5 lg:flex-row lg:items-start">
            {/* 좌: 승인 대기 목록 300px (§9-3) */}
            <div className="flex w-full shrink-0 flex-col gap-2.5 lg:w-[300px]">
              <p className="text-table-head font-extrabold tracking-[0.04em] text-text-sub">
                승인 대기 목록
              </p>
              {pending.length === 0 ? (
                <p className="rounded-card-s border border-border bg-white px-4 py-3.5 text-caption text-text-sub">
                  승인 대기 중인 후보가 없습니다.
                </p>
              ) : (
                pending.map((c) => {
                  const active = selected?.id === c.id;
                  return (
                    <button
                      key={c.id}
                      type="button"
                      aria-pressed={active}
                      onClick={() => {
                        setSelectedId(c.id);
                        setJustApprovedId(null);
                      }}
                      className={`flex flex-col gap-1.5 rounded-card-s border px-4 py-3.5 text-left ${
                        active
                          ? "border-primary bg-primary-light"
                          : "border-border bg-white hover:border-primary"
                      }`}
                    >
                      <span className="flex w-full items-center justify-between gap-1.5">
                        <span className="font-mono text-[12.5px] font-bold text-primary">
                          {c.id.slice(0, 8).toUpperCase()}
                        </span>
                        <span className="rounded-chip bg-warning-light px-2 py-0.5 text-[12px] font-bold text-warning">
                          승인 대기
                        </span>
                      </span>
                      <span className="text-note leading-[1.4] font-bold text-text">
                        {c.title}
                      </span>
                      <span className="flex flex-wrap gap-x-3 text-table-head text-text-sub">
                        {cardMeta(c).map((m) => (
                          <span key={m}>{m}</span>
                        ))}
                      </span>
                    </button>
                  );
                })
              )}
              {/* 최종 폴리시 9: 영문 사유 코드는 화면에 표시하지 않는다 */}
              <p className="px-0.5 text-table-head leading-[1.5] text-text-faint">
                지원 범위 내 <b>근거 부족</b> 실패에서만 후보가 생성됩니다.
              </p>
            </div>

            {/* 우: 상세 카드 */}
            <div className="min-w-0 flex-1">
              {selected ? (
                <KbCandidateReview
                  key={`${role}:${selected.id}`}
                  candidate={selected}
                  sourceFailure={failures.get(selected.failed_question_id)}
                  actor={actor}
                  busy={busyId === selected.id}
                  justApproved={justApprovedId === selected.id}
                  /* fixture 판정 비활성 (Q-PM-DEMO-001) - ACTIVE 전환은 actual 전용 */
                  reviewLocked={mode === "fixture"}
                  onReview={(id, decision, comment) =>
                    void review(id, decision, comment)
                  }
                  onNext={goNext}
                />
              ) : (
                <EmptyState
                  title="승인 대기 후보가 없습니다"
                  description="실패 질문 관리에서 '근거 부족' 건에 대해 KB 후보 초안을 생성하면 이 목록에 올라옵니다."
                  action={
                    <Link
                      href="/admin/failures"
                      className="inline-flex min-h-11 items-center rounded-btn-s border border-primary bg-white px-4 text-admin-body font-bold text-primary hover:bg-primary-light active:bg-primary-light"
                    >
                      실패 질문 관리로 이동
                    </Link>
                  }
                />
              )}
            </div>
          </div>
        )}
      </div>

      {toast && <Toast message={toast} onDone={() => setToast(null)} />}
    </main>
  );
}
