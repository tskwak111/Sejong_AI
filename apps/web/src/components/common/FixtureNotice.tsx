/**
 * 시연용 샘플 데이터 상시 배너 - fixture 모드에서만 전 화면 최상단 노출
 * (태성 리뷰 2). 공지 배너(NoticeBanner)와 혼동되지 않도록 앰버(warning)
 * 톤을 쓴다 - warning 토큰은 대비 4.5:1 이상 (globals.css).
 */
export default function FixtureNotice() {
  return (
    <p
      role="status"
      className="border-b border-warning/30 bg-warning-light px-4 py-2 text-center text-note font-bold text-warning"
    >
      시연용 샘플 — 공식 데이터 아님
    </p>
  );
}
