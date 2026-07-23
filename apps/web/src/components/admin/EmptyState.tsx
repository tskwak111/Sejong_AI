/**
 * 빈 상태 UI - DESIGN.md v3 §14: 아이콘 + 상황 설명 + 다음 행동 안내.
 * 밋밋한 "데이터가 없습니다" 금지. 이음센터 세 화면 공용.
 */
export default function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center rounded-panel border border-border bg-white px-6 py-12 text-center">
      <span className="flex h-12 w-12 items-center justify-center rounded-cell bg-primary-light text-primary">
        <svg
          aria-hidden="true"
          className="h-6 w-6"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth={1.8}
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M22 12h-6l-2 3h-4l-2-3H2" />
          <path d="M5.5 5.1 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.5-6.9A2 2 0 0 0 16.7 4H7.3a2 2 0 0 0-1.8 1.1Z" />
        </svg>
      </span>
      <p className="mt-4 text-admin-body font-bold text-text">{title}</p>
      <p className="mt-1 text-admin-body text-text-sub">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
