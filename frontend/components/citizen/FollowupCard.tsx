"use client";

/**
 * (B) FOLLOWUP 후속질문 카드 - DESIGN.md v3 §6-2 (시안 2a).
 * 단정적 답변을 절대 보여주지 않는다. 헤더 뱃지 "확인 질문" +
 * 리드 문장 + 선택지 버튼(56px, 1.5px primary-border, 제목+보조 설명).
 * 선택 직후: 카드가 요약형으로 전환 - 선택 칩 primary 채움 + ✓,
 * 미선택 형제 opacity 0.45 + border-soft. 그 아래 답변 카드가 이어진다.
 */
import { useState } from "react";
import type { FollowupResponse } from "@/types/api";
import RegionSelect from "@/components/citizen/RegionSelect";
import FeedbackButtons from "@/components/citizen/FeedbackButtons";

export default function FollowupCard({
  response,
  responseId,
  onSelectQuestion,
  onSelectRegion,
}: {
  response: FollowupResponse;
  responseId: string;
  /** QUERY 선택지 클릭 → 해당 질문을 새로 전송 */
  onSelectQuestion: (question: string) => void;
  /** REGION 선택지에서 동 선택 → region_question을 동 조건과 함께 전송 */
  onSelectRegion: (dong: string, regionQuestion: string) => void;
}) {
  const [regionOpen, setRegionOpen] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  /** REGION 선택지로 고른 동 - 요약형 칩 라벨에 병기 */
  const [selectedDong, setSelectedDong] = useState<string | null>(null);

  /* ---- 선택 직후 요약형 (§6-2) ---- */
  if (selectedId !== null) {
    return (
      <div className="card-enter flex flex-col gap-2 rounded-card border border-border bg-white p-4 shadow-card">
        <p className="text-label font-bold text-text-sub">{response.message}</p>
        <ul className="flex flex-col gap-2">
          {response.options.map((opt) => {
            const selected = opt.id === selectedId;
            return (
              <li key={opt.id}>
                {selected ? (
                  <div className="flex min-h-14 w-full items-center justify-between gap-2 rounded-btn bg-primary px-4 py-2.5">
                    <span className="text-body font-bold text-white">
                      {opt.label}
                      {selectedDong && ` (${selectedDong})`}
                    </span>
                    <span
                      aria-hidden="true"
                      className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-white/25 text-[13px] font-extrabold text-white"
                    >
                      ✓
                    </span>
                  </div>
                ) : (
                  <div className="flex min-h-11 w-full items-center rounded-btn border-[1.5px] border-border-soft px-4 py-2 opacity-45">
                    <span className="text-[16px] font-semibold text-text-sub">
                      {opt.label}
                    </span>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      </div>
    );
  }

  /* ---- 선택 전 ---- */
  return (
    <article className="card-enter overflow-hidden rounded-card border border-border bg-white shadow-card">
      {/* 헤더 뱃지 - SUCCESS 유형 뱃지와 동일 문법 */}
      <div className="border-b border-border-soft bg-card-head px-4 py-3.5">
        <span className="inline-flex rounded-[8px] border border-primary-border bg-primary-light px-2.5 py-1 text-caption font-extrabold text-primary">
          확인 질문
        </span>
      </div>

      <div className="flex flex-col gap-3.5 p-4">
        {/* 리드 문장 */}
        <p className="text-body-lg font-semibold text-text [text-wrap:pretty]">
          {response.message}
        </p>

        {/* 선택지 - 전체 폭, 56px, 1.5px primary-border, 제목 + 보조 설명 */}
        <ul className="flex flex-col gap-2">
          {response.options.map((opt) => (
            <li key={opt.id}>
              <button
                type="button"
                aria-expanded={opt.kind === "REGION" ? regionOpen : undefined}
                onClick={() => {
                  if (opt.kind === "REGION") {
                    setRegionOpen((v) => !v);
                  } else if (opt.next_question) {
                    setSelectedId(opt.id);
                    onSelectQuestion(opt.next_question);
                  }
                }}
                className={`flex min-h-14 w-full flex-col items-start gap-px rounded-btn border-[1.5px] px-4 py-2.5 text-left ${
                  opt.kind === "REGION" && regionOpen
                    ? "border-primary bg-hover-tint"
                    : "border-primary-border bg-white hover:border-primary hover:bg-hover-tint active:bg-hover-tint"
                }`}
              >
                <span className="flex items-center gap-1.5 text-body font-bold text-primary">
                  {opt.kind === "REGION" && (
                    <svg
                      aria-hidden="true"
                      className="h-5 w-5 shrink-0"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth={1.8}
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 0 1 16 0Z" />
                      <circle cx="12" cy="10" r="3" />
                    </svg>
                  )}
                  {opt.label}
                </span>
                {opt.description && (
                  <span className="text-caption font-medium text-text-sub">
                    {opt.description}
                  </span>
                )}
              </button>
            </li>
          ))}
        </ul>

        {/* 지역(동) 선택 - REGION 옵션 펼침 (SFR-004) */}
        {regionOpen && response.region_question && (
          <div className="rounded-cell bg-bg-sub p-3">
            <RegionSelect
              label="어느 동에 거주하시나요?"
              onSelect={(dong) => {
                setRegionOpen(false);
                const regionOpt = response.options.find(
                  (o) => o.kind === "REGION",
                );
                if (regionOpt) setSelectedId(regionOpt.id);
                setSelectedDong(dong);
                onSelectRegion(dong, response.region_question!);
              }}
            />
          </div>
        )}

        {/* 하단 안내 */}
        <p className="text-note leading-[1.5] text-text-sub">
          골라도 되고, 질문을 다시 써도 돼요. 선택하시면{" "}
          <b className="font-bold text-text">공식 출처를 확인해</b> 답해드립니다.
        </p>

        {/* 관련 민원 한 줄 제안 - §6-1-9와 같은 문법의 행 */}
        {response.related_suggestion && (
          <p className="rounded-btn bg-card-head px-3.5 py-3 text-note leading-[1.45] text-text-sub">
            {response.related_suggestion}
          </p>
        )}
      </div>

      {/* 만족/불만족 - 모든 응답 공통 (§6-5) */}
      <FeedbackButtons responseId={responseId} />
    </article>
  );
}
