/**
 * (D) 로딩 스켈레톤 - DESIGN.md v3 §6-4 (시안 2c). 답변 카드 구조 예고:
 * 헤더(뱃지 자리 + 확인 뱃지 자리) → 본문 2줄 → 번호 원 + 텍스트 스텝 2개 →
 * 출처 블록 자리(64px, verify-light + 초록 계열 테두리) → 스피너 + 안내 문구.
 * 목표 응답 3초(PER-001), 무한 스피너 금지 - 10초 초과 시 오류 카드로 전환.
 */
export default function LoadingSkeleton() {
  return (
    <div
      role="status"
      aria-label="공식 자료에서 확인하고 있어요"
      className="overflow-hidden rounded-card border border-border bg-white shadow-card"
    >
      {/* 헤더 - 뱃지 자리 + 확인 뱃지 자리 */}
      <div className="flex items-center justify-between border-b border-border-soft bg-card-head px-4 py-3.5">
        <span className="h-[26px] w-24 animate-pulse rounded-[8px] bg-border-soft" />
        <span className="h-[18px] w-30 animate-pulse rounded-[8px] bg-bg-sub" />
      </div>
      <div className="flex flex-col gap-4 p-4">
        {/* 본문 2줄 */}
        <div className="flex flex-col gap-2">
          <span className="h-4 w-[92%] animate-pulse rounded-chip bg-border-soft" />
          <span className="h-4 w-[74%] animate-pulse rounded-chip bg-border-soft" />
        </div>
        {/* 번호 원 + 텍스트 스텝 2개 */}
        <div className="flex flex-col gap-2.5">
          <div className="flex items-center gap-3">
            <span className="h-7 w-7 shrink-0 animate-pulse rounded-full bg-border-soft" />
            <span className="h-3.5 w-[60%] animate-pulse rounded-chip bg-bg-sub" />
          </div>
          <div className="flex items-center gap-3">
            <span className="h-7 w-7 shrink-0 animate-pulse rounded-full bg-border-soft" />
            <span className="h-3.5 w-[48%] animate-pulse rounded-chip bg-bg-sub" />
          </div>
        </div>
        {/* 출처 블록 자리 - 초록 계열 (출처가 올 것임을 예고) */}
        <div className="h-16 animate-pulse rounded-card-s border border-verify-border bg-verify-light" />
        {/* 스피너 + 안내 문구 (PER-001 - 3초 심리 방어선) */}
        <p className="flex items-center gap-2.5">
          <span
            aria-hidden="true"
            className="h-[18px] w-[18px] shrink-0 animate-spin rounded-full border-[3px] border-primary-border border-t-primary"
          />
          <span className="text-[16px] font-semibold text-text-sub">
            공식 자료에서 확인하고 있어요. 보통 3초 안에 답해드려요.
          </span>
        </p>
      </div>
    </div>
  );
}
