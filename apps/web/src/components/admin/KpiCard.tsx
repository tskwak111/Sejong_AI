"use client";

/**
 * KPI 카드 - DESIGN.md v3 §9-1 + 이음센터 모바일 정비 2·3.
 * - 768px 이상(카드): 라벨 13.5px 700 text-sub → 값 28px 800 tabular-nums +
 *   단위 15px text-sub → 목표 캡션 13px faint → 판정 뱃지.
 * - 768px 미만(가로 스트립, 높이 64px 내외): 좌측 = 지표명 15px + 목표 캡션
 *   13px faint 세로 2줄, 우측 = 값 22px bold tabular-nums + 판정 뱃지.
 * - 지표명은 탭 가능(물음표 12px 원형 아이콘) - 하단 "지표 안내"의 해당 항목으로
 *   앵커 이동. 데스크톱에서도 동일 동작 허용 (정비 3).
 * 장식 아이콘·스파크라인·증감 화살표·차트 금지.
 */

/**
 * §9-1 목표 대비 판정. 최종 폴리시 12: 뱃지는 목표 판정(달성/미달)에만 쓴다 -
 * 목표가 없는 집계 지표(총 질문 수·폴백률)는 judgement를 생략하고
 * 캡션 "집계 지표"만 표시한다.
 */
export interface KpiJudgement {
  label: string;
  tone: "success" | "warning";
}

const JUDGE_TONE: Record<KpiJudgement["tone"], string> = {
  success: "bg-verify-light-2 text-verify-dark",
  warning: "bg-warning-light text-warning",
};

export default function KpiCard({
  label,
  value,
  unit,
  target,
  judgement,
  subCaption,
  guideId,
  onGuideClick,
}: {
  label: string;
  value: string;
  /** 값 단위 - 예: "건" / "%" / "초" */
  unit?: string;
  /** 목표 캡션 - 예: "목표 80% 이상" / "집계 지표" */
  target: string;
  /** 목표 판정 뱃지 - 목표가 없는 집계 지표는 생략 (최종 폴리시 12) */
  judgement?: KpiJudgement;
  /** 보조 캡션 - 폴백률 카드 전용. 모바일 스트립에는 표시하지 않는다(정비 2 구성 고정) */
  subCaption?: string;
  /** 하단 "지표 안내" 해당 항목의 id - 지표명 탭 시 앵커 이동 (정비 3) */
  guideId: string;
  onGuideClick: (guideId: string) => void;
}) {
  return (
    <div className="flex min-h-16 items-center justify-between gap-3 rounded-card-s border border-border bg-white px-4 py-1.5 md:min-h-0 md:flex-col md:items-stretch md:justify-start md:gap-2 md:p-4">
      {/* 좌측(모바일) - 지표명(탭 → 지표 안내 앵커) + 목표 캡션 세로 2줄 */}
      <div className="flex min-w-0 flex-col md:contents">
        <button
          type="button"
          onClick={() => onGuideClick(guideId)}
          className="flex min-h-11 items-center gap-1 self-start text-left text-[15px] font-bold text-text-sub hover:text-text md:order-1 md:min-h-0 md:text-kpi-label"
        >
          {label}
          {/* 물음표 12px 원형 - 탭 가능함의 표지 (정비 3) */}
          <svg
            aria-hidden="true"
            className="h-3 w-3 shrink-0"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={2.4}
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <circle cx="12" cy="12" r="10" />
            <path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 2.4-3 4" />
            <path d="M12 17.5h.01" />
          </svg>
          <span className="sr-only">지표 안내 보기</span>
        </button>
        <p className="text-table-head text-text-faint md:order-3">{target}</p>
      </div>
      {/* 우측(모바일) - 값 + 판정 뱃지 */}
      <div className="flex shrink-0 items-center gap-2.5 md:contents">
        <p className="text-[22px] font-bold tracking-[-0.01em] text-text tabular-nums md:order-2 md:text-kpi md:font-extrabold">
          {value}
          {unit && (
            <span className="ml-0.5 text-note font-semibold text-text-sub">
              {unit}
            </span>
          )}
        </p>
        {judgement && (
          <span
            className={`rounded-chip px-2 py-[3px] text-[12.5px] font-extrabold whitespace-nowrap md:order-4 md:self-start ${JUDGE_TONE[judgement.tone]}`}
          >
            {judgement.label}
          </span>
        )}
      </div>
      {subCaption && (
        <p className="hidden text-table-head text-text-sub md:order-5 md:block">
          {subCaption}
        </p>
      )}
    </div>
  );
}
