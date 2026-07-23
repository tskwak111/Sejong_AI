/**
 * 서비스 로고 - 승인된 심볼(logo-symbol.png)의 SVG 재현. (DESIGN.md v2 §3-A)
 * 두 점을 잇는 수평 S커브: 좌점 → 골 → 마루 → 우점.
 * 라운드 캡 스트로크 path + 양끝 circle, 점 지름 = 선 굵기의 약 1.6배.
 * 색은 currentColor 단색 - 사용처에서 text-primary 토큰 클래스로 지정.
 * favicon(app/icon.svg)은 축약형(좌측 점 + 첫 곡선)을 별도 제작.
 */
export default function Logo({
  className = "h-8 w-8",
}: {
  className?: string;
}) {
  return (
    <svg
      aria-hidden="true"
      className={className}
      viewBox="0 0 24 24"
      fill="none"
    >
      <path
        d="M4.6 13.9C6.4 16.4 9.3 16.6 12 12.2C14.7 7.8 17.6 8.1 19.4 10.6"
        stroke="currentColor"
        strokeWidth={2}
        strokeLinecap="round"
      />
      <circle cx="4.6" cy="13.9" r="1.6" fill="currentColor" />
      <circle cx="19.4" cy="10.6" r="1.6" fill="currentColor" />
    </svg>
  );
}

/**
 * 워드마크 - 심볼 + "세종 민원이음" (Pretendard Bold 조합).
 * 시민 헤더·이음센터 사이드바·관문 화면 공용.
 * 브랜드 문법(최종 폴리시 4 + 볼드 수정): "세종" text-sub 볼드 / "민원" text /
 * "이음" primary - 공유되는 "이음"의 파랑이 브랜드 실.
 * tone="inverse": 어두운 배경용 흰 변형 - "이음"만 밝은 하늘색(tie-line).
 */
export function Wordmark({
  symbolClassName = "h-7 w-7",
  textClassName = "text-card-title",
  tone = "default",
}: {
  symbolClassName?: string;
  textClassName?: string;
  tone?: "default" | "inverse";
}) {
  const inverse = tone === "inverse";
  return (
    <span className="inline-flex items-center gap-2">
      <span
        className={`shrink-0 ${inverse ? "text-white" : "text-primary"}`}
      >
        <Logo className={symbolClassName} />
      </span>
      <span
        className={`font-bold ${inverse ? "text-white" : "text-text"} ${textClassName}`}
      >
        <span className={inverse ? "text-admin-nav-soft" : "text-text"}>
          세종
        </span>{" "}
        민원
        <span className={inverse ? "text-tie-line" : "text-primary"}>이음</span>
      </span>
    </span>
  );
}
