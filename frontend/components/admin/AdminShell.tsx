"use client";

/**
 * 이음센터 공통 셸 - DESIGN.md v3 §5-1 사이드바 (216px, --color-admin-nav).
 * - 브랜드: 로고 심볼 흰색 변형 + "세종 민원이음 관리자"(12.5px, tie-line 색)
 *   + "이음센터" 20px 800 흰색.
 * - 메뉴: P0 3개 라우팅만. 그 외 메뉴 금지 (P1 비활성 표기는 최종 폴리시 11로 제거).
 *   활성 = 흰 배경 + admin-nav 텍스트 800. 건수 뱃지(실패 질문=신규, KB=승인 대기).
 * - 최하단 철학 카드: 화면별 문구 (§5-1).
 * - 대비: 흰색 14.3:1, #C8D6EA 9.7:1, #9DB8DC 7.1:1 - admin-nav 배경 위 4.5:1 충족.
 *
 * [결정 근거] 2026-07-22, 무인 세션: /admin/login(관문)은 셸 없이 렌더링.
 * metadata(title) export를 위해 layout.tsx(서버)와 셸(클라이언트)을 분리했다.
 */
import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import Logo from "@/components/common/Logo";
import { fetchFailureQueue, fetchKbCandidates } from "@/lib/api";

const MENU = [
  // 표시 라벨만 "운영 현황" - 라우팅 경로·파일명·컴포넌트명은 불변.
  // tabLabel = 768px 미만 가로 탭 표기 (세션 3 후속 수정 3)
  { href: "/admin", label: "운영 현황", tabLabel: "운영 현황" },
  { href: "/admin/failures", label: "실패 질문", tabLabel: "실패 질문" },
  { href: "/admin/kb-candidates", label: "KB 후보 승인", tabLabel: "KB 후보" },
];

/** §5-1 사이드바 최하단 철학 카드 - 화면별 문구 */
const PHILOSOPHY: Record<string, React.ReactNode> = {
  "/admin": (
    <>
      KPI는 기대 효과 추정치를
      <br />
      <b className="text-white">실측값으로 대체</b>하는 근거입니다.
    </>
  ),
  "/admin/failures": (
    <>
      근거 부족 실패만
      <br />
      <b className="text-white">KB 후보로 전환</b>됩니다.
    </>
  ),
  "/admin/kb-candidates": (
    <>
      AI는 제안하고,
      <br />
      <b className="text-white">판정은 담당자가 합니다.</b>
      <br />
      승인된 KB만 시민 답변에 사용돼요.
    </>
  ),
};

export default function AdminShell({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const pathname = usePathname();
  const [counts, setCounts] = useState<{ failures: number; kb: number } | null>(
    null,
  );

  // 메뉴 건수 뱃지 - 페이지 이동 시 + 페이지 내 상태 변경(admin:data-changed
  // 이벤트) 시 갱신 (mock 조회 재사용, 신규 데이터 아님)
  useEffect(() => {
    if (pathname === "/admin/login") return;
    let alive = true;
    const refresh = () => {
      void Promise.all([fetchFailureQueue(), fetchKbCandidates()]).then(
        ([failures, candidates]) => {
          if (!alive) return;
          setCounts({
            failures: failures.filter((f) => f.status === "신규").length,
            kb: candidates.filter((c) => c.status === "승인 대기").length,
          });
        },
      );
    };
    refresh();
    window.addEventListener("admin:data-changed", refresh);
    return () => {
      alive = false;
      window.removeEventListener("admin:data-changed", refresh);
    };
  }, [pathname]);

  // 관문 화면은 셸 없이 그대로
  if (pathname === "/admin/login") return <>{children}</>;

  const badgeOf = (href: string): number | null => {
    if (counts === null) return null;
    if (href === "/admin/failures") return counts.failures;
    if (href === "/admin/kb-candidates") return counts.kb;
    return null;
  };

  return (
    <div className="min-h-screen md:flex">
      {/* 768px 미만: 상단 고정 바 - 로고 줄 56px + 메뉴 탭 줄 48px(한 단계
          밝은 네이비), 탭 터치 44px 이상 (모바일 정비 1). 활성 탭 = 하단 2px
          흰 보더, 가로 스크롤 허용. */}
      <header className="sticky top-0 z-40 bg-admin-nav md:hidden">
        <div className="flex h-14 items-center justify-between gap-2 px-4">
          {/* 워드마크 문법(최종 폴리시 4): 흰 변형은 "이음"만 밝은 하늘색 */}
          <span className="flex items-center gap-1.5 text-[17px] font-extrabold text-white">
            <Logo className="h-5 w-5 shrink-0 text-white" />
            <span>
              <span className="text-tie-line">이음</span>센터
            </span>
          </span>
          <span className="text-table-head font-semibold text-admin-nav-soft">
            운영 관리자
          </span>
        </div>
        <nav aria-label="관리자 메뉴 (모바일)" className="bg-white/[0.07]">
          <ul className="flex h-12 overflow-x-auto px-2">
            {MENU.map((m) => {
              const active = pathname === m.href;
              const badge = badgeOf(m.href);
              return (
                <li key={m.href} className="shrink-0">
                  <Link
                    href={m.href}
                    aria-current={active ? "page" : undefined}
                    className={`flex h-12 items-center gap-1.5 border-b-2 px-3 text-note whitespace-nowrap ${
                      active
                        ? "border-white font-extrabold text-white"
                        : "border-transparent font-semibold text-admin-nav-soft hover:text-white"
                    }`}
                  >
                    {m.tabLabel}
                    {badge !== null && badge > 0 && (
                      <span
                        className={`rounded-pill px-1.5 py-px text-[12px] font-bold tabular-nums ${
                          active
                            ? "bg-primary text-white"
                            : "bg-white/15 text-white"
                        }`}
                      >
                        {badge}
                      </span>
                    )}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
      </header>

      <aside className="hidden w-[216px] shrink-0 flex-col gap-[22px] bg-admin-nav px-3.5 py-[22px] md:flex">
        {/* 브랜드 - 로고 심볼 흰색 변형 (§5-1) */}
        <div className="px-2">
          <span className="flex items-center gap-1.5 text-[12.5px] font-semibold text-tie-line">
            <Logo className="h-4 w-4 shrink-0 text-white" />
            세종 민원이음 관리자
          </span>
          {/* 워드마크 문법(최종 폴리시 4): 흰 변형은 "이음"만 밝은 하늘색 */}
          <p className="mt-0.5 text-[20px] font-extrabold text-white">
            <span className="text-tie-line">이음</span>센터
          </p>
        </div>

        <nav aria-label="관리자 메뉴">
          <ul className="flex flex-col gap-1">
            {MENU.map((m) => {
              const active = pathname === m.href;
              const badge = badgeOf(m.href);
              return (
                <li key={m.href}>
                  <Link
                    href={m.href}
                    aria-current={active ? "page" : undefined}
                    className={`flex min-h-11 items-center justify-between gap-2 rounded-btn-s px-3 py-[11px] text-note ${
                      active
                        ? "bg-white font-extrabold text-admin-nav"
                        : "font-semibold text-admin-nav-soft hover:bg-white/[0.08] hover:text-white"
                    }`}
                  >
                    <span>{m.label}</span>
                    {badge !== null && badge > 0 && (
                      <span
                        className={`rounded-pill px-2 py-0.5 text-[12.5px] font-bold tabular-nums ${
                          active
                            ? "bg-primary text-white"
                            : "bg-white/15 text-white"
                        }`}
                      >
                        {badge}
                      </span>
                    )}
                  </Link>
                </li>
              );
            })}
            {/* "민원 통계 P1" 비활성 항목은 최종 폴리시 11로 제거 -
                눌리지 않는 메뉴는 두지 않는다. P1 로드맵은 발표 자료에서 다룬다. */}
          </ul>
        </nav>

        {/* 최하단 철학 카드 (§5-1) */}
        <div className="mt-auto rounded-btn bg-white/[0.07] p-3 text-table-head leading-[1.5] text-admin-nav-soft">
          {PHILOSOPHY[pathname] ?? PHILOSOPHY["/admin"]}
        </div>
      </aside>
      <div className="min-w-0 flex-1 bg-bg-admin">{children}</div>
    </div>
  );
}
