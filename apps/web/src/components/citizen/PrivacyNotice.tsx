/**
 * 개인정보 입력 경고 - 입력창 바로 아래 8px 상시 노출 (DESIGN.md v3 §8-4).
 * 15px, 자물쇠 아이콘 포함, 대비 4.5:1 이상 (text-sub 6.1:1).
 * 첫 화면·대화 화면 입력바 공용.
 */
export default function PrivacyNotice() {
  return (
    <p className="mt-2 flex items-center gap-1.5 text-note text-text-sub">
      <svg
        aria-hidden="true"
        className="h-4 w-4 shrink-0"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <rect x="4" y="11" width="16" height="10" rx="2" />
        <path d="M8 11V7a4 4 0 0 1 8 0v4" />
      </svg>
      <span className="min-w-0">
        주민등록번호·전화번호 등{" "}
        <strong className="font-bold text-text">
          개인정보는 입력하지 마세요
        </strong>
      </span>
    </p>
  );
}
