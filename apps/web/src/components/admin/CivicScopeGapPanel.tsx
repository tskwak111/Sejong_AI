"use client";

import { useMemo, useState } from "react";
import type { components } from "../../../../../packages/shared-contracts/src/generated/api";

type CivicScopeGapSummary = components["schemas"]["CivicScopeGapSummary"];
type CivicScopeGapStatus = components["schemas"]["CivicScopeGapStatus"];
type Decision = components["schemas"]["CivicScopeGapReviewRequest"]["decision"];

type Props = Readonly<{
  items: CivicScopeGapSummary[];
  canReview: boolean;
  busyId: string | null;
  onReview: (id: string, decision: Decision, comment: string) => void;
}>;

const FILTERS: ReadonlyArray<{ value: CivicScopeGapStatus; label: string }> = [
  { value: "NEW", label: "신규" },
  { value: "PLANNED", label: "검토 계획" },
  { value: "DISMISSED", label: "목록 제외" },
];

export default function CivicScopeGapPanel({ items, canReview, busyId, onReview }: Props) {
  const [filter, setFilter] = useState<CivicScopeGapStatus>("NEW");
  const [selected, setSelected] = useState<CivicScopeGapSummary | null>(null);
  const [comment, setComment] = useState("");
  const visible = useMemo(() => items.filter((item) => item.status === filter), [filter, items]);

  const review = (decision: Decision) => {
    if (!selected || !comment.trim()) return;
    onReview(selected.id, decision, comment.trim());
    setSelected(null);
    setComment("");
  };

  return (
    <section aria-labelledby="scope-gap-title" className="mt-7 border-t border-border pt-6">
      <h2 id="scope-gap-title" className="text-[20px] font-extrabold text-text">
        지원 범위 검토
      </h2>
      <p className="mt-1 text-caption text-text-sub">
        민원으로 보이지만 현재 4개 지원 분야에 없는 질문입니다. 실패 질문·KB 후보와 분리해 마스킹 문구만 30일 보관합니다.
      </p>
      <div role="group" aria-label="지원 범위 검토 상태" className="mt-3 flex flex-wrap gap-2">
        {FILTERS.map(({ value, label }) => (
          <button key={value} type="button" aria-pressed={filter === value} onClick={() => setFilter(value)} className={`min-h-11 rounded-pill px-4 text-note font-bold ${filter === value ? "bg-primary text-white" : "border border-border bg-white text-text-sub"}`}>
            {label} {items.filter((item) => item.status === value).length}
          </button>
        ))}
      </div>
      {visible.length === 0 ? (
        <p className="mt-3 rounded-card-s border border-border bg-white px-4 py-4 text-caption text-text-sub">
          이 상태의 지원 범위 검토 항목이 없습니다.
        </p>
      ) : (
        <ul className="mt-3 grid gap-3">
          {visible.map((item) => (
            <li key={item.id} className="rounded-card-s border border-border bg-white p-4">
              <p className="text-admin-body font-bold text-text">
                {item.masked_question ?? "보관 기간이 지나 질문 문구가 파기되었습니다."}
              </p>
              <p className="mt-1 text-table-head text-text-sub">
                {item.status === "NEW" ? "자동 후보 생성 없음" : item.review_comment}
              </p>
              {item.status === "NEW" && canReview && (
                <button type="button" onClick={() => setSelected(item)} className="mt-3 min-h-11 rounded-btn-s border border-primary px-4 text-note font-bold text-primary">
                  범위 검토
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
      {selected && (
        <div role="dialog" aria-modal="true" aria-labelledby="scope-review-title" className="fixed inset-0 z-50 grid place-items-center bg-black/40 p-4">
          <div className="w-full max-w-lg rounded-card bg-white p-5 shadow-xl">
            <h3 id="scope-review-title" className="text-[19px] font-extrabold text-text">지원 범위 검토 의견</h3>
            <label className="mt-4 grid gap-1.5 text-note font-bold text-text">
              검토 의견 (필수)
              <textarea autoFocus rows={4} value={comment} onChange={(e) => setComment(e.target.value)} className="rounded-btn-s border border-border p-3 text-admin-body focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20" />
            </label>
            <div className="mt-4 flex flex-wrap justify-end gap-2">
              <button type="button" onClick={() => setSelected(null)} className="min-h-11 rounded-btn-s border border-border px-4 font-bold text-text-sub">취소</button>
              <button type="button" disabled={!comment.trim() || busyId === selected.id} onClick={() => review("DISMISSED")} className="min-h-11 rounded-btn-s border border-danger px-4 font-bold text-danger disabled:opacity-40">목록에서 제외</button>
              <button type="button" disabled={!comment.trim() || busyId === selected.id} onClick={() => review("PLANNED")} className="min-h-11 rounded-btn-s bg-primary px-4 font-bold text-white disabled:opacity-40">다음 범위로 검토</button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
