import ChatScreen from "./chat-screen";

/**
 * 시민 대화 화면 - mock/실API 전환은 server-only 환경변수로만 결정한다
 * (apps/web 기존 방식: ADMIN_UI_MODE와 동일 문법).
 * 태성 리뷰 2: 미설정 시 기본은 actual - same-origin /api/v1/chat
 * (Next rewrite → API_INTERNAL_BASE_URL)이며, 연결 실패는 값 없는 오류
 * 카드로 안전 처리된다. 데모 5문항 fixture(로컬 시연 버전, 제안서 7.4)는
 * CHAT_UI_MODE=fixture 명시 설정에서만 켜지고 상단 샘플 배너가 따라온다.
 */
export const dynamic = "force-dynamic";

export default function ChatPage() {
  const transportMode =
    process.env.CHAT_UI_MODE === "fixture" ? "fixture" : "actual";

  return <ChatScreen transportMode={transportMode} />;
}
