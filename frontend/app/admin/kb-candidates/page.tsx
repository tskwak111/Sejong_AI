"use client";

/**
 * KB 후보 승인 - CLAUDE.md §6 (3) + DESIGN.md v3 §9-3.
 * - 레이아웃: 좌측 승인 대기 목록 300px(카드형) + 우측 상세 카드.
 * - 상태: 승인 대기 → 승인 / 반려(사유 코드). 승인 주체: 운영 관리자.
 * - 승인 직후 상세 카드가 완료형(ACTIVE + 승인 스탬프)으로 전환 + 토스트 병행.
 * - 실패 질문 mock을 함께 조회해 후보별 "발단이 된 실패 질문" 이력을 표시.
 */
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import type {
  FailureQueueItem,
  KbCandidate,
  KbRejectReason,
} from "@/types/api";
import {
  fetchFailureQueue,
  fetchKbCandidates,
  reviewKbCandidate,
} from "@/lib/api";
import KbCandidateReview from "@/components/admin/KbCandidateReview";
import EmptyState from "@/components/admin/EmptyState";
import PageHeader from "@/components/admin/PageHeader";
import Toast from "@/components/common/Toast";

/** 담당자 표시 (§5-2) + 승인 스탬프 표기 - 최종 폴리시 10: 가상 실명 미사용 */
const REVIEWER_LABEL = "운영 관리자";

export default function AdminKbCandidatesPage() {
  const [items, setItems] = useState<KbCandidate[] | null>(null);
  const [failures, setFailures] = useState<Map<string, FailureQueueItem>>(
    new Map(),
  );
  const [busyId, setBusyId] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [justApprovedId, setJustApprovedId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setRefreshing(true);
    try {
      const [list, failureList] = await Promise.all([
        fetchKbCandidates(),
        fetchFailureQueue(),
      ]);
      // 승인 대기 우선 + 최신순
      list.sort((a, b) => {
        if ((a.status === "승인 대기") !== (b.status === "승인 대기")) {
          return a.status === "승인 대기" ? -1 : 1;
        }
        return b.created_at.localeCompare(a.created_at);
      });
      setItems(list);
      setFailures(new Map(failureList.map((f) => [f.id, f])));
      setLastUpdated(new Date());
    } finally {
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const review = async (
    id: string,
    status: "승인" | "반려",
    reasonCode?: KbRejectReason,
  ) => {
    setBusyId(id);
    try {
      await reviewKbCandidate(id, status, reasonCode);
      if (status === "승인") {
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
      // 사이드바 건수 뱃지 갱신 (AdminShell이 수신)
      window.dispatchEvent(new Event("admin:data-changed"));
    } finally {
      setBusyId(null);
    }
  };

  const pending = (items ?? []).filter((c) => c.status === "승인 대기");
  const pendingCount = pending.length;

  // 선택된 후보 - 명시 선택이 없으면 대기 목록 첫 건.
  // 판정이 끝난 후보는 승인 직후 완료형(justApproved)일 때만 상세에 남는다.
  const selected =
    (items ?? []).find(
      (c) =>
        c.id === selectedId &&
        (c.status === "승인 대기" || c.id === justApprovedId),
    ) ??
    pending[0] ??
    null;

  /** 완료형의 "다음 후보 보기 →" - 다음 대기 건으로 전환 */
  const goNext = () => {
    setJustApprovedId(null);
    setSelectedId(pending[0]?.id ?? null);
  };

  /** 대기 목록 카드의 메타 - "실패 N회 / 출처 검증 상태" (§9-3) */
  const cardMeta = (c: KbCandidate): string[] => {
    const meta: string[] = [];
    const repeat = failures.get(c.source_failure_id)?.repeat_count;
    if (repeat) meta.push(`실패 ${repeat}회`);
    meta.push(c.draft.source_url === null ? "출처 검증 필요" : "출처 검증 완료");
    return meta;
  };

  return (
    <main>
      <PageHeader
        title="KB 후보 승인"
        subtitle={
          <>
            <span>실패 질문에서 AI가 작성한 초안</span>
            <span>운영 관리자가 승인하면 ACTIVE로 반영</span>
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
            {/* 담당자 표시 (§5-2) - 최종 폴리시 10: 이니셜 아바타 대신 일반 아이콘 */}
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
                {REVIEWER_LABEL}
              </span>
            </span>
          </>
        }
        lastUpdated={lastUpdated}
        refreshing={refreshing}
        onRefresh={() => void load()}
      />

      <div className="px-5 py-[22px] md:px-7">
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
                          {c.id.toUpperCase()}
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
                  key={selected.id}
                  candidate={selected}
                  sourceFailure={failures.get(selected.source_failure_id)}
                  busy={busyId === selected.id}
                  justApproved={justApprovedId === selected.id}
                  approverName={REVIEWER_LABEL}
                  onReview={(id, status, reason) =>
                    void review(id, status, reason)
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
