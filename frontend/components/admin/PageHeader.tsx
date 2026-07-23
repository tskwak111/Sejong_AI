"use client";

/**
 * 이음센터 상단바 - DESIGN.md v3 §5-2 (전 페이지 공통).
 * 흰 배경 전체 폭 + 하단 1px border-soft.
 * 좌측: 페이지 제목(--t-title) + 부제 14px text-sub.
 * 우측: 페이지별 메타(meta) + "마지막 갱신 {시각}" + 새로고침 버튼.
 * lastUpdated는 호출부의 마지막 데이터 로드 시각 (mock 시연에서는 실제 fetch 시각).
 */
function formatTime(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export default function PageHeader({
  title,
  subtitle,
  meta,
  lastUpdated,
  refreshing = false,
  onRefresh,
}: {
  title: string;
  /** 부제 한 줄 - 예: "모든 지표는 비식별 로그 기준" */
  subtitle?: React.ReactNode;
  /** 페이지별 우측 메타 - 예: "최근 30일" 필, "신규 N건", 담당자 표시 (§5-2) */
  meta?: React.ReactNode;
  lastUpdated: Date | null;
  refreshing?: boolean;
  onRefresh: () => void;
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-3 border-b border-border-soft bg-white px-5 py-[18px] md:px-7">
      <div>
        <h1 className="text-title font-extrabold text-text">{title}</h1>
        {subtitle && (
          <p className="mt-0.5 flex flex-wrap gap-x-4 text-caption text-text-sub">
            {subtitle}
          </p>
        )}
      </div>
      <div className="flex flex-wrap items-center gap-3.5">
        {meta}
        <span className="text-table-head text-text-sub tabular-nums">
          {lastUpdated
            ? `마지막 갱신 ${formatTime(lastUpdated)}`
            : "불러오는 중…"}
        </span>
        <button
          type="button"
          onClick={onRefresh}
          disabled={refreshing}
          className="flex min-h-11 items-center gap-1.5 rounded-btn-s border border-border bg-white px-4 text-caption font-semibold text-text-sub hover:bg-bg-sub hover:text-text active:bg-bg-sub disabled:opacity-60"
        >
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
            <path d="M21 12a9 9 0 1 1-2.6-6.4L21 8" />
            <path d="M21 3v5h-5" />
          </svg>
          {refreshing ? "불러오는 중…" : "새로고침"}
        </button>
      </div>
    </div>
  );
}
