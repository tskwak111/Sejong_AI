"use client";

/**
 * 지역(동) 선택 UI - SFR-004.
 * 사용처: ① FOLLOWUP의 "지역" 선택지 ② 답변 카드 "우리 동 찾기" 인라인.
 * 별도 온보딩 화면은 만들지 않는다. 선택 동은 React state로만 유지 (§8, §9).
 * 선택 칩 규칙 (DESIGN.md v3 §11): 기본 outline / 선택 = primary 채움 + ✓.
 */
import { SEJONG_DONGS } from "@/lib/mock";

export default function RegionSelect({
  current,
  onSelect,
  label = "동 선택",
}: {
  current?: string;
  onSelect: (dong: string) => void;
  label?: string;
}) {
  return (
    <fieldset>
      <legend className="mb-2 text-body font-bold text-text">{label}</legend>
      <ul className="grid grid-cols-3 gap-2 md:grid-cols-4">
        {SEJONG_DONGS.map((dong) => {
          const selected = dong === current;
          return (
            <li key={dong}>
              <button
                type="button"
                aria-pressed={selected}
                onClick={() => onSelect(dong)}
                className={`flex min-h-11 w-full items-center justify-center gap-1 rounded-btn-s px-2 py-2 text-body ${
                  selected
                    ? "bg-primary font-bold text-white"
                    : "border border-border bg-white text-text hover:border-primary hover:bg-hover-tint active:bg-hover-tint"
                }`}
              >
                {selected && (
                  <span aria-hidden="true" className="text-[13px] font-extrabold">
                    ✓
                  </span>
                )}
                {dong}
              </button>
            </li>
          );
        })}
      </ul>
    </fieldset>
  );
}
