"use client";

/**
 * 지역(동) 선택 UI - SFR-004.
 * 사용처: ① FOLLOWUP의 지역 선택지 ② 답변 카드 "동 변경" 인라인.
 * 별도 온보딩 화면은 만들지 않는다. 선택 동은 React state로만 유지 (§8, §9).
 * 선택 칩 규칙 (DESIGN.md v3 §11): 기본 outline / 선택 = primary 채움 + ✓.
 * 목록은 계약 selected_region enum 3개동 한정 (lib/labels.ts REGION_OPTIONS).
 */
import { REGION_OPTIONS, isRegion, regionSelectCopy, type Region } from "@/lib/labels";

export default function RegionSelect({
  current,
  onSelect,
  label,
}: {
  current?: string | null;
  onSelect: (dong: Region) => void;
  label?: string;
}) {
  const selectedRegion = isRegion(current ?? "") ? (current as Region) : null;
  const copy = label ?? regionSelectCopy(selectedRegion);

  return (
    <div>
      <label className="mb-1 block text-label font-bold text-text" htmlFor="region-select">
        {copy}
      </label>
      <select
        id="region-select"
        value={selectedRegion ?? ""}
        onChange={(event) => {
          if (isRegion(event.target.value)) onSelect(event.target.value);
        }}
        className="min-h-11 w-full rounded-btn-s border border-border bg-white px-3 text-body font-semibold text-text focus:border-primary"
      >
        <option value="">거주 지역 선택 · 선택사항</option>
        {REGION_OPTIONS.map((dong) => (
          <option key={dong} value={dong}>
            {dong} · 변경
          </option>
        ))}
      </select>
    </div>
  );
}
