"use client";

/**
 * 답변 실패 질문 관리 - CLAUDE.md §6 (2) + DESIGN.md v3 §9-2.
 * - 필터 칩(r-pill, 활성=primary 채움) + 칩 위 요약 한 줄 (전체 N건 / 신규 N건)
 * - 신규 도착 하이라이트: 새로고침 후 새로 등장한 행 highlight→2초 페이드 (1회성)
 * - 상태 변경/초안 생성 시 확인 토스트 + KB 후보 화면 이동 배너
 * - INSUFFICIENT_GROUNDING 건에만 "KB 후보 생성" 노출, NULL 파기 행 안전 렌더링
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import type { FailureQueueItem, FailureStatus, FallbackCode } from "@/types/api";
import { FALLBACK_CODE_LABEL } from "@/types/api";
import {
  createKbDraft,
  fetchFailureQueue,
  fetchKbCandidates,
  updateFailureStatus,
} from "@/lib/api";
import FailureTable from "@/components/admin/FailureTable";
import EmptyState from "@/components/admin/EmptyState";
import PageHeader from "@/components/admin/PageHeader";
import Toast from "@/components/common/Toast";

type Filter = "ALL" | FallbackCode;

const FILTERS: { key: Filter; label: string }[] = [
  { key: "ALL", label: "전체" },
  { key: "INSUFFICIENT_GROUNDING", label: FALLBACK_CODE_LABEL.INSUFFICIENT_GROUNDING },
  { key: "PERSONAL_LOOKUP", label: FALLBACK_CODE_LABEL.PERSONAL_LOOKUP },
  { key: "LEGAL_JUDGMENT", label: FALLBACK_CODE_LABEL.LEGAL_JUDGMENT },
  { key: "OUT_OF_SCOPE", label: FALLBACK_CODE_LABEL.OUT_OF_SCOPE },
];

/** 상태 변경 토스트용 표시 라벨 (내부 값 불변) */
const STATUS_DISPLAY: Record<FailureStatus, string> = {
  신규: "신규",
  검토중: "검토 중",
  처리완료: "처리 완료",
};

/**
 * 직전 로드의 id 집합 - 모듈 스코프로 유지해 페이지를 떠났다 돌아와도
 * "새로 등장한" 행을 판별한다 (§9-2 - 데모 #5에서 시민 폴백이 도착하는
 * 순간을 하이라이트로 보이게 하는 장치). 탭 리로드 시에만 초기화.
 */
let knownFailureIds: Set<string> | null = null;

export default function AdminFailuresPage() {
  const [items, setItems] = useState<FailureQueueItem[] | null>(null);
  const [draftedIds, setDraftedIds] = useState<Set<string>>(new Set());
  const [filter, setFilter] = useState<Filter>("ALL");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [draftBanner, setDraftBanner] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [highlightIds, setHighlightIds] = useState<Set<string>>(new Set());

  const load = useCallback(async () => {
    setRefreshing(true);
    try {
      const [failures, candidates] = await Promise.all([
        fetchFailureQueue(),
        fetchKbCandidates(),
      ]);
      // 최초 로드는 하이라이트 없음, 이후엔 새로 등장한 id만 1회성 하이라이트.
      // fresh가 있을 때만 갱신 - StrictMode의 이펙트 2회 실행이 빈 Set으로
      // 덮어써 하이라이트를 지우는 것을 방지 (애니메이션은 1회성이라 잔류 무해)
      if (knownFailureIds !== null) {
        const fresh = failures
          .filter((f) => !knownFailureIds!.has(f.id))
          .map((f) => f.id);
        if (fresh.length > 0) setHighlightIds(new Set(fresh));
      }
      knownFailureIds = new Set(failures.map((f) => f.id));
      setItems(failures);
      setDraftedIds(new Set(candidates.map((c) => c.source_failure_id)));
      setLastUpdated(new Date());
    } finally {
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const changeStatus = async (id: string, status: FailureStatus) => {
    setBusyId(id);
    try {
      await updateFailureStatus(id, status);
      await load();
      // 사이드바 건수 뱃지 갱신 (AdminShell이 수신)
      window.dispatchEvent(new Event("admin:data-changed"));
      setToast(`상태가 '${STATUS_DISPLAY[status]}'(으)로 변경되었습니다`);
    } finally {
      setBusyId(null);
    }
  };

  const createDraft = async (id: string) => {
    setBusyId(id);
    try {
      const draft = await createKbDraft(id);
      if (draft) {
        setDraftBanner(draft.title);
        setToast("KB 후보 초안이 생성되었습니다");
      }
      await load();
      window.dispatchEvent(new Event("admin:data-changed"));
    } finally {
      setBusyId(null);
    }
  };

  const filtered = useMemo(
    () =>
      (items ?? []).filter(
        (i) => filter === "ALL" || i.fallback_code === filter,
      ),
    [items, filter],
  );

  const countOf = (key: Filter) =>
    (items ?? []).filter((i) => key === "ALL" || i.fallback_code === key)
      .length;

  const newCount = (items ?? []).filter((i) => i.status === "신규").length;

  return (
    <main>
      <PageHeader
        title="답변 실패 질문 관리"
        subtitle={
          <>
            <span>시민 화면에서 답하지 못한 질문이 폴백 사유별로 모입니다</span>
            <span>텍스트는 근거 부족 실패만 30일 보관 후 파기</span>
          </>
        }
        meta={
          items !== null ? (
            <span className="text-caption text-text-sub">
              신규{" "}
              <b className="text-[16px] font-extrabold text-primary tabular-nums">
                {newCount}
              </b>
              건
            </span>
          ) : undefined
        }
        lastUpdated={lastUpdated}
        refreshing={refreshing}
        onRefresh={() => void load()}
      />

      <div className="px-5 py-[22px] md:px-7">
        {/* 초안 생성 배너 - 데모 #5: 승인 화면으로 매끄럽게 전환 */}
        {draftBanner && (
          <div className="mb-4 flex flex-wrap items-center justify-between gap-2 rounded-btn border border-primary-border bg-primary-light px-4 py-3">
            <p className="text-admin-body text-text">
              KB 후보 초안이 생성되었습니다:{" "}
              <span className="font-bold">{draftBanner}</span>
            </p>
            <Link
              href="/admin/kb-candidates"
              className="min-h-11 shrink-0 content-center rounded-btn-s bg-primary px-4 text-admin-body font-bold text-white hover:bg-primary-dark active:bg-primary-dark"
            >
              KB 후보 승인으로 이동
            </Link>
          </div>
        )}

        {/* 요약 한 줄 - §13-1: 구분자 가운뎃점 없이 여백 구분 */}
        {items !== null && (
          <p className="flex flex-wrap gap-x-3 text-note text-text-sub">
            <span>전체 {items.length}건</span>
            <span>신규 {newCount}건</span>
          </p>
        )}

        {/* 폴백 사유 4종 필터 - r-pill, 활성=primary 채움 (§9-2).
            768px 미만은 한 줄 유지 + 가로 스크롤 허용 (모바일 정비 4 - 칩 행은
            가로 스크롤 0건 목표의 유일한 예외) */}
        <div
          role="group"
          aria-label="폴백 사유 필터"
          className="mt-2 flex gap-2 overflow-x-auto pb-1 md:flex-wrap md:overflow-x-visible md:pb-0"
        >
          {FILTERS.map(({ key, label }) => {
            const active = filter === key;
            const count = countOf(key);
            return (
              <button
                key={key}
                type="button"
                aria-pressed={active}
                onClick={() => setFilter(key)}
                /* 0건 칩은 40% 투명, 형태·클릭 유지(클릭 시 빈 상태 표시).
                   사유 4종이 항상 보이는 것 자체가 정보다. 활성 시엔 불투명 복원 */
                className={`min-h-11 shrink-0 rounded-pill px-[18px] text-[14.5px] whitespace-nowrap ${
                  active
                    ? "bg-primary font-extrabold text-white hover:bg-primary-dark"
                    : "border border-border bg-white font-bold text-text-sub hover:border-primary hover:text-primary"
                } ${count === 0 && !active ? "opacity-40" : ""}`}
              >
                {label} {count}
              </button>
            );
          })}
        </div>

        <div className="mt-3.5">
          {items === null ? (
            <p className="text-admin-body text-text-sub">불러오는 중…</p>
          ) : filtered.length === 0 ? (
            <EmptyState
              title={
                filter === "ALL"
                  ? "아직 실패 질문이 없습니다"
                  : `'${FILTERS.find((f) => f.key === filter)?.label}' 사유의 실패 질문이 없습니다`
              }
              description="시민 화면에서 폴백이 발생하면 이 목록에 새로 들어옵니다. 새로고침으로 확인해 보세요."
              action={
                <button
                  type="button"
                  onClick={() => void load()}
                  className="min-h-11 rounded-btn-s border border-primary bg-white px-4 text-admin-body font-bold text-primary hover:bg-primary-light active:bg-primary-light"
                >
                  새로고침
                </button>
              }
            />
          ) : (
            <FailureTable
              items={filtered}
              draftedFailureIds={draftedIds}
              busyId={busyId}
              highlightIds={highlightIds}
              onChangeStatus={(id, status) => void changeStatus(id, status)}
              onCreateDraft={(id) => void createDraft(id)}
            />
          )}
        </div>
      </div>

      {toast && <Toast message={toast} onDone={() => setToast(null)} />}
    </main>
  );
}
