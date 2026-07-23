import type { Metadata } from "next";
import { notFound } from "next/navigation";
import AdminShell from "@/components/admin/AdminShell";

/**
 * 이음센터 레이아웃 - server-only local/private 게이트 (apps/web 기존 방식).
 * ADMIN_UI_ENABLED=true가 아니면 모든 /admin 경로는 404다. 이는 인증을
 * 대체하지 않으며 public 관리자 연결은 계속 금지한다 (openapi
 * x-admin-exposure-policy). ADMIN_UI_MODE=actual일 때만 typed actual admin
 * transport를 쓰고, 그 외에는 명시적 fixture다.
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
  const mode = process.env.ADMIN_UI_MODE === "actual" ? "actual" : "fixture";

  return <AdminShell mode={mode}>{children}</AdminShell>;
}
