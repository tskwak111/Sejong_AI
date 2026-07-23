"use client";

/**
 * 시민 첫 화면 - DESIGN.md v3.1 §8 (구조는 v2 유지, 색·간격·반경·타이포는 v3 토큰).
 * 공지 배너 → 헤더(로고 + 소속 표기) → 검색 밴드(primary-light 전체 폭:
 * 히어로 + 질문 입력창 + 개인정보 경고 + 신뢰 스트립 3항목) →
 * "안내해 드리는 4개 분야"(분야 아이콘 + 예시 질문 칩 2개) → 공공형 푸터.
 * 분야 4개는 계약 SupportedIntent enum 기준 (lib/labels.ts).
 */
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  NoticeBanner,
  CitizenHeader,
  PublicFooter,
} from "@/components/citizen/PageChrome";
import PrivacyNotice from "@/components/citizen/PrivacyNotice";
import {
  INTENT_LABEL,
  SUPPORTED_INTENTS,
  type SupportedIntent,
} from "@/lib/labels";

/* 분야별 예시 질문 칩 2개 - 탭하면 해당 질문으로 대화 시작 (§8-4, SFR-006) */
const CATEGORY_CHIPS: Record<SupportedIntent, string[]> = {
  MOVE_IN_RESIDENT_REGISTRATION: [
    "전입신고는 언제까지 해야 하나요?",
    "이사했는데 뭐 해야 하나요?",
  ],
  BULKY_WASTE: [
    "아름동에서 대형폐기물은 언제 내놓나요?",
    "대형폐기물 수수료는 얼마인가요?",
  ],
  CERTIFICATE_ISSUANCE: [
    "주민등록등본은 어떻게 발급받나요?",
    "등본 발급 수수료는 얼마인가요?",
  ],
  LOCAL_TAX_GENERAL: ["자동차세는 언제 내나요?", "제 자동차세 얼마 나왔나요?"],
};

/* 포커스 시 placeholder가 분야를 순환하는 예시 질문 (§8-3, §12 허용 목록) */
const PLACEHOLDER_ROTATION = [
  "예: 전입신고는 언제까지 해야 하나요?",
  "예: 아름동에서 대형폐기물은 언제 내놓나요?",
  "예: 주민등록등본은 어떻게 발급받나요?",
  "예: 자동차세는 언제 내나요?",
];

/* 분야별 라인 아이콘 (lucide 계열, 인라인 SVG) - §8-4 */
const CATEGORY_ICON_PATHS: Record<SupportedIntent, React.ReactNode> = {
  MOVE_IN_RESIDENT_REGISTRATION: (
    <>
      <path d="M3 11.5 12 4l9 7.5" />
      <path d="M5.5 10.2V20h13v-9.8" />
      <path d="M10 20v-5.5h4V20" />
    </>
  ),
  BULKY_WASTE: (
    <>
      <path d="M5 11V8a3 3 0 0 1 3-3h8a3 3 0 0 1 3 3v3" />
      <path d="M3 13a2 2 0 0 1 4 0v1h10v-1a2 2 0 0 1 4 0v4H3v-4Z" />
      <path d="M6 17v2M18 17v2" />
    </>
  ),
  CERTIFICATE_ISSUANCE: (
    <>
      <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8Z" />
      <path d="M14 3v5h5" />
      <path d="M9 13h6M9 17h4" />
    </>
  ),
  LOCAL_TAX_GENERAL: (
    <>
      <rect x="2.5" y="5.5" width="19" height="13" rx="2" />
      <path d="M2.5 10h19" />
      <path d="M6 15h4" />
    </>
  ),
};

function CategoryIcon({ category }: { category: SupportedIntent }) {
  return (
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
      {CATEGORY_ICON_PATHS[category]}
    </svg>
  );
}

/* 신뢰 스트립 3항목 (§8-3) - 점 구분자 없이 여백으로 구분 */
const TRUST_ITEMS = ["공식 출처 표기", "최종 확인일 안내", "담당 기관 연결"];

export default function HomePage() {
  const router = useRouter();
  const [question, setQuestion] = useState("");
  const [placeholderIdx, setPlaceholderIdx] = useState(0);
  const [focused, setFocused] = useState(false);
  const reducedMotion = useRef(false);

  useEffect(() => {
    reducedMotion.current = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
  }, []);

  // §12: 포커스 중 placeholder 3초마다 분야 순환 (reduced-motion 시 고정)
  useEffect(() => {
    if (!focused || reducedMotion.current) return;
    const t = setInterval(
      () => setPlaceholderIdx((i) => (i + 1) % PLACEHOLDER_ROTATION.length),
      3000,
    );
    return () => clearInterval(t);
  }, [focused]);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const q = question.trim();
    if (!q) return;
    router.push(`/chat?q=${encodeURIComponent(q)}`);
  };

  return (
    <div className="flex min-h-screen flex-col bg-bg">
      <NoticeBanner />
      <CitizenHeader />

      <main id="main" className="flex-1">
        {/* §8-3 검색 밴드 - primary-light 전체 폭, 내용은 680px 컬럼 */}
        <div className="bg-primary-light">
          <div className="mx-auto w-full max-w-[680px] px-5 pb-8">
            {/* 히어로 - 상하 여백 24px 이내, 제목-부제 간격 8px */}
            <section className="pt-6 pb-5">
              <h1 className="text-title font-extrabold text-text">
                궁금한 민원을 물어보세요
              </h1>
              <p className="mt-2 text-body text-text-sub">
                세종시 민원, 물어보면 근거와 함께 안내해 드려요
              </p>
            </section>

            {/* 질문 입력창 - 화면의 주인공: 높이 60px, 2px primary 테두리 상시 */}
            <form onSubmit={submit}>
              <label htmlFor="question-input" className="sr-only">
                질문 입력
              </label>
              <div className="flex h-[60px] items-center gap-1 rounded-btn border-2 border-primary bg-white p-1.5 shadow-card focus-within:[box-shadow:var(--focus-ring)]">
                <input
                  id="question-input"
                  type="text"
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  onFocus={() => setFocused(true)}
                  onBlur={() => setFocused(false)}
                  placeholder={PLACEHOLDER_ROTATION[placeholderIdx]}
                  className="h-full min-w-0 flex-1 bg-transparent px-3 text-body text-text placeholder:text-text-faint focus:outline-none"
                />
                <button
                  type="submit"
                  className="flex h-full shrink-0 items-center gap-1.5 rounded-btn-s bg-primary px-4 text-body font-bold text-white hover:bg-primary-dark active:bg-primary-dark md:px-5"
                >
                  <svg
                    aria-hidden="true"
                    className="h-5 w-5"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth={2}
                    strokeLinecap="round"
                  >
                    <circle cx="11" cy="11" r="7" />
                    <path d="m20 20-3.8-3.8" />
                  </svg>
                  질문하기
                </button>
              </div>
              {/* 개인정보 경고 - 입력창 아래 8px 상시 노출 */}
              <PrivacyNotice />
            </form>

            {/* 신뢰 스트립 3항목 - 체크 아이콘, 점 구분자 없이 여백 구분.
                모바일 세로 스택, 데스크톱 한 줄 gap 32px */}
            <ul className="mt-5 flex flex-col gap-1.5 md:flex-row md:items-center md:gap-8">
              {TRUST_ITEMS.map((item) => (
                <li
                  key={item}
                  className="flex items-center gap-1.5 text-note text-text"
                >
                  <svg
                    aria-hidden="true"
                    className="h-4 w-4 shrink-0 text-primary"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth={2.2}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="M20 6 9 17l-5-5" />
                  </svg>
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* §8-4 "안내해 드리는 4개 분야" - 분야 아이콘 + 예시 질문 칩 2개 */}
        <section
          aria-labelledby="scope-heading"
          className="mx-auto w-full max-w-[680px] px-5 pt-8 pb-8"
        >
          <h2
            id="scope-heading"
            className="text-card-title font-extrabold text-text"
          >
            안내해 드리는 4개 분야
          </h2>
          <ul className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
            {SUPPORTED_INTENTS.map((key) => (
              <li
                key={key}
                className="rounded-card-s border border-border bg-white p-5 shadow-card"
              >
                <div className="flex items-center gap-2.5">
                  <span className="text-primary">
                    <CategoryIcon category={key} />
                  </span>
                  <p className="text-card-title font-bold text-text">
                    {INTENT_LABEL[key]}
                  </p>
                </div>
                <ul className="mt-3 space-y-2">
                  {CATEGORY_CHIPS[key].map((q) => (
                    <li key={q}>
                      {/* 예시 질문 칩 - min-height 52px, 전체 폭, outline */}
                      <Link
                        href={`/chat?q=${encodeURIComponent(q)}`}
                        className="flex min-h-[52px] items-center rounded-btn-s border border-border bg-white px-3 py-2 text-note text-text hover:border-primary hover:bg-hover-tint hover:text-primary active:bg-hover-tint"
                      >
                        {q}
                      </Link>
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ul>
        </section>
      </main>

      <PublicFooter />
    </div>
  );
}
