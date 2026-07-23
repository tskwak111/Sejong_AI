import type { Metadata } from "next";
import { notFound } from "next/navigation";
import AdminShell from "@/components/admin/AdminShell";

/**
 * 이음센터 레이아웃 - server-only local/private 게이트 (apps/web 기존 방식).
 * ADMIN_UI_ENABLED=true가 아니면 모든 /admin 경로는 404다. 이는 인증을
 * 대체하지 않으며 public 관리자 연결은 계속 금지한다 (openapi
 * x-admin-exposure-policy). 태성 리뷰 2: 미설정 시 기본은 actual(typed
 * admin transport, 실패 시 화면별 오류 상태)이고, fixture는
 * ADMIN_UI_MODE=fixture 명시 설정에서만 켜지며 상단 샘플 배너가 따라온다.
 */
export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  // v2 §1: 이음센터 페이지 title (최종 폴리시 1: 줄표 금지)
  title: "이음센터 | 세종 민원이음 운영센터",
};

export default function AdminLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  if (process.env.ADMIN_UI_ENABLED !== "true") {
    notFound();
  }
  const mode = process.env.ADMIN_UI_MODE === "fixture" ? "fixture" : "actual";

  return <AdminShell mode={mode}>{children}</AdminShell>;
}
