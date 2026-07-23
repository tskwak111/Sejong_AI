import type { Metadata } from "next";
import "@/styles/globals.css";

export const metadata: Metadata = {
  // v2 §1: 시민 화면 페이지 title (최종 폴리시 1: 줄표 금지)
  title: "세종 민원이음 | 세종특별자치시 민원 안내",
  description:
    "세종특별자치시 민원 안내 AI. 승인된 지식베이스에 근거해서만 답합니다.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ko">
      <head>
        {/*
          Pretendard GOV (가변, dynamic subset) - DESIGN.md §14-1.
          orioncactus/pretendard 공식 배포본 (npm: pretendard-gov@1.3.9).
          font-display: swap은 배포 CSS에 포함. 미로드 폴백은 --font-sans의
          시스템 산세리프 스택 (globals.css).
        */}
        <link
          rel="stylesheet"
          href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-gov-dynamic-subset.min.css"
        />
      </head>
      <body className="min-h-screen antialiased">
        {/* v2 §1: 스킵 링크 - 포커스 시에만 보임 */}
        <a
          href="#main"
          className="skip-link rounded-btn-s bg-primary px-4 py-2 text-note font-semibold text-white"
        >
          본문 바로가기
        </a>
        {children}
      </body>
    </html>
  );
}
