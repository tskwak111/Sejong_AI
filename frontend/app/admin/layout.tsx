import type { Metadata } from "next";
import AdminShell from "@/components/admin/AdminShell";

export const metadata: Metadata = {
  // v2 §1: 이음센터 페이지 title (최종 폴리시 1: 줄표 금지)
  title: "이음센터 | 세종 민원이음 운영센터",
};

export default function AdminLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return <AdminShell>{children}</AdminShell>;
}
