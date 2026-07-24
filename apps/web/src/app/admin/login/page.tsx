"use client";

/**
 * 이음센터 관문 화면 - DESIGN.md v3 §9-4.
 * 전면 admin-nav 배경 + 중앙 흰 카드 400px(r-card, shadow-raised).
 * 아이디/비밀번호 입력(52px, label 연결) + 로그인(검증 없이 /admin 이동, 시연) +
 * 시연 고지 주의 박스 + 감사 로그 캡션.
 * 시민 화면 어디에도 이 경로 링크를 노출하지 않는다.
 */
import { useRouter } from "next/navigation";

export default function AdminLoginPage() {
  const router = useRouter();

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    // 시연: 검증 없이 통과 (실인증은 발주기관 계정 체계 연동 예정)
    router.push("/admin");
  };

  return (
    <main id="main" tabIndex={-1} className="flex min-h-screen items-center justify-center bg-admin-nav px-4">
      <div className="w-full max-w-[400px] rounded-card bg-white p-[30px] pt-8 shadow-raised">
        <p className="text-table-head font-semibold text-text-sub">
          세종 민원이음 관리자
        </p>
        {/* 워드마크 문법(최종 폴리시 4): "이음" primary + "센터" text */}
        <h1 className="mt-0.5 text-[26px] font-extrabold text-text">
          <span className="text-primary">이음</span>센터
        </h1>

        <form onSubmit={submit} className="mt-5 space-y-3">
          <div>
            <label
              htmlFor="admin-id"
              className="mb-1.5 block text-note font-bold text-text"
            >
              아이디
            </label>
            <input
              id="admin-id"
              type="text"
              autoComplete="username"
              className="min-h-[52px] w-full rounded-btn border border-border bg-white px-3.5 text-body text-text placeholder:text-text-faint focus:border-primary"
              placeholder="아이디를 입력하세요"
            />
          </div>
          <div>
            <label
              htmlFor="admin-password"
              className="mb-1.5 block text-note font-bold text-text"
            >
              비밀번호
            </label>
            <input
              id="admin-password"
              type="password"
              autoComplete="current-password"
              className="min-h-[52px] w-full rounded-btn border border-border bg-white px-3.5 text-body text-text placeholder:text-text-faint focus:border-primary"
              placeholder="비밀번호를 입력하세요"
            />
          </div>
          <button
            type="submit"
            className="min-h-14 w-full rounded-btn bg-primary px-4 text-[18px] font-extrabold text-white hover:bg-primary-dark active:bg-primary-dark"
          >
            로그인
          </button>
        </form>

        {/* 시연 고지 - 주의 박스 (§9-4) */}
        <div className="mt-5 rounded-btn bg-warning-light px-3.5 py-3 text-[14.5px] leading-[1.5] font-semibold text-warning">
          시연 버전입니다. 실제 행정망 계정과 연결되어 있지 않아요. 실인증은
          발주기관 계정 체계와 연동 예정입니다.
        </div>
        {/* 최종 폴리시 14: 시연 버전은 실제로 기록하지 않으므로 단정 문구 금지 */}
        <p className="mt-3 text-table-head text-text-faint">
          실서비스에서는 접속 기록이 감사 로그로 관리됩니다.
        </p>
      </div>
    </main>
  );
}
