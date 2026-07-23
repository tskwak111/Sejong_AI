import ChatScreen from "./chat-screen";

/**
 * 시민 대화 화면 - mock/실API 전환은 server-only 환경변수로만 결정한다
 * (apps/web 기존 방식: ADMIN_UI_MODE와 동일 문법).
 * CHAT_UI_MODE=actual일 때만 same-origin /api/v1/chat(Next rewrite →
 * API_INTERNAL_BASE_URL)을 쓰고, 그 외에는 데모 5문항 fixture다
 * (mock 모드 = 로컬 시연 버전, 제안서 7.4).
 */
export const dynamic = "force-dynamic";

export default function ChatPage() {
  const transportMode =
    process.env.CHAT_UI_MODE === "actual" ? "actual" : "fixture";

  return <ChatScreen transportMode={transportMode} />;
}
