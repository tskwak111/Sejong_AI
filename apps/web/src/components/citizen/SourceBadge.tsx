/**
 * 출처 스트립 - SUCCESS 카드 하단 (세션 3 후속 수정 1: 카드의 유일한 출처 표시).
 * verify 문법: --verify-tint 배경 + --verify-border 상단 보더 + 초록 체크.
 * 구성(좌→우): 아이콘 + "공식 출처 확인" + 문서명(semibold) + 확인일 + 원문 보기.
 * source_id는 시민 화면 어디에도 표시하지 않는다 (최종 폴리시 8) -
 * 데이터(계약 Source.source_id)와 이음센터 표기는 유지.
 * KPI "출처 표기율 100%"의 프론트 보증 장치 (CLAUDE.md §4-A).
 */
import type { components } from "../../../../../packages/shared-contracts/src/generated/api";

type Source = components["schemas"]["Source"];

export default function SourceBadge({ sources }: { sources: Source[] }) {
  return (
    <div className="border-t border-verify-border bg-verify-light px-4 py-3">
      <ul className="space-y-1">
        {sources.map((s, i) => (
          <li
            key={s.source_id}
            /* §13-1: " · " 구분자 금지 - 요소 간 여백, 확인일은 색으로 자연 구분 */
            className="flex flex-wrap items-center gap-x-3 gap-y-1 text-note"
          >
            {i === 0 && (
              <span className="flex items-center gap-1.5 font-bold text-verify-dark">
                <span
                  aria-hidden="true"
                  className="flex h-4 w-4 items-center justify-center rounded-full bg-verify text-[10px] text-white"
                >
                  ✓
                </span>
                공식 출처 확인
              </span>
            )}
            {/* 최종 폴리시 8: source_id는 시민 화면 미표시 (데이터·이음센터에는 유지) */}
            <span className="font-semibold text-text">{s.title}</span>
            <span className="text-text-sub">{s.last_verified_at} 확인 기준</span>
            {s.url && (
              <a
                href={s.url}
                target="_blank"
                rel="noopener noreferrer"
                /* 터치 대상 44px 확보 (§14) - 세로 패딩으로 히트 영역 확장 */
                className="-my-2.5 inline-flex min-h-11 items-center gap-0.5 py-2.5 text-primary underline hover:text-primary-dark"
              >
                원문 보기
                <svg
                  aria-hidden="true"
                  className="h-3.5 w-3.5"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={2}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M15 3h6v6" />
                  <path d="M10 14 21 3" />
                  <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
                </svg>
              </a>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
